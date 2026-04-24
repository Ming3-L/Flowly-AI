from __future__ import annotations

import asyncio
import json
from typing import Any

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from ai_engine.models import Workflow, WorkflowExecution
from ai_engine.workflow import WorkflowEventEmitter
from ai_engine.workflow_execution_tracking import activity_for_canvas_node
from ai_engine.workflow_nodes.execution import execute_canvas_node


def _as_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("text"), str):
        return obj["text"]
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _guess_media_type(url: str) -> str:
    u = (url or "").lower()
    if any(u.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
        return "image"
    if any(u.endswith(ext) for ext in (".mp3", ".wav", ".m4a", ".ogg", ".webm")):
        return "audio"
    if any(u.endswith(ext) for ext in (".mp4", ".mov", ".webm", ".mkv")):
        return "video"
    return ""


def _extract_media_items(out_obj: Any, *, node_id: str) -> list[dict[str, Any]]:
    """
    从节点输出中抽取媒体 URL（图片/音频/视频）为统一结构。
    输出项约定：{type, url, node_id, field}
    """
    if not isinstance(out_obj, dict):
        return []
    items: list[dict[str, Any]] = []
    candidates: list[tuple[str, Any, str]] = [
        ("image", out_obj.get("generated_image_url"), "generated_image_url"),
        ("image", out_obj.get("image_url"), "image_url"),
        ("audio", out_obj.get("audio_url"), "audio_url"),
        ("video", out_obj.get("video_url"), "video_url"),
        ("", out_obj.get("url"), "url"),
    ]
    for hinted_type, raw, field in candidates:
        if not raw:
            continue
        url = str(raw).strip()
        if not url:
            continue
        mtype = hinted_type or _guess_media_type(url) or ""
        if not mtype:
            continue
        items.append({"type": mtype, "url": url, "node_id": node_id, "field": field})
    return items


def _build_graph(definition: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    nodes = definition.get("nodes") or []
    edges = definition.get("edges") or []
    node_by_id: dict[str, dict[str, Any]] = {}
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            node_by_id[str(n["id"])] = n
    edge_list: list[dict[str, Any]] = []
    for e in edges:
        if isinstance(e, dict) and e.get("id"):
            edge_list.append(e)
    return node_by_id, edge_list


def _incoming_edges(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    inc: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        tgt = str(e.get("targetNodeId") or "")
        if not tgt:
            continue
        inc.setdefault(tgt, []).append(e)
    return inc


def _outgoing_edges(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        src = str(e.get("sourceNodeId") or "")
        if not src:
            continue
        out.setdefault(src, []).append(e)
    return out


def _detect_cycle(nodes: set[str], edges: list[dict[str, Any]]) -> bool:
    # Kahn's algorithm on node ids
    indeg: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        s = str(e.get("sourceNodeId") or "")
        t = str(e.get("targetNodeId") or "")
        if s in indeg and t in indeg:
            indeg[t] += 1
    q = [nid for nid, d in indeg.items() if d == 0]
    seen = 0
    out = _outgoing_edges(edges)
    while q:
        nid = q.pop()
        seen += 1
        for e in out.get(nid, []):
            t = str(e.get("targetNodeId") or "")
            if t in indeg:
                indeg[t] -= 1
                if indeg[t] == 0:
                    q.append(t)
    return seen != len(nodes)


def _sync_mark_execution_running(ex_pk: int) -> None:
    with transaction.atomic():
        ex0 = WorkflowExecution.objects.select_for_update().get(pk=ex_pk)
        ex0.status = "running"
        ex0.save(update_fields=["status"])


def _sync_save_execution_completed(ex_pk: int, result: dict[str, Any]) -> None:
    ex = WorkflowExecution.objects.get(pk=ex_pk)
    ex.status = "completed"
    ex.output_data = result
    ex.completed_at = timezone.now()
    ex.save(update_fields=["status", "output_data", "completed_at"])


def _sync_save_execution_failed(ex_pk: int, err: str) -> None:
    ex = WorkflowExecution.objects.get(pk=ex_pk)
    ex.status = "failed"
    ex.error_message = err[:4000]
    ex.output_data = {"error": err}
    ex.completed_at = timezone.now()
    ex.save(update_fields=["status", "error_message", "output_data", "completed_at"])


_mark_execution_running = sync_to_async(_sync_mark_execution_running, thread_sensitive=True)
_save_execution_completed = sync_to_async(_sync_save_execution_completed, thread_sensitive=True)
_save_execution_failed = sync_to_async(_sync_save_execution_failed, thread_sensitive=True)


async def run_canvas_workflow_async(
    *,
    workflow: Workflow,
    execution: WorkflowExecution,
    thread_id: str,
    user_id: int,
    entry_node_id: str | None = None,
    initial_inputs: dict[str, Any] | None = None,
) -> None:
    """
    画布串联执行（方案 B）：逐节点执行 + 通过 WebSocket 推送进度与中间输出。
    """
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=execution.id)

    node_by_id, edges = _build_graph(workflow.definition if isinstance(workflow.definition, dict) else {})
    node_ids = set(node_by_id.keys())

    try:
        await _mark_execution_running(execution.pk)

        if not node_ids:
            raise ValueError("workflow.definition.nodes 为空，无法执行")
        if _detect_cycle(node_ids, edges):
            raise ValueError("画布存在环路，暂不支持执行")

        inc = _incoming_edges(edges)
        out = _outgoing_edges(edges)

        # Entry node: explicit > single in-degree-0 > first node
        if entry_node_id and entry_node_id in node_by_id:
            entry = entry_node_id
        else:
            indeg0 = [nid for nid in node_ids if len(inc.get(nid, [])) == 0]
            entry = indeg0[0] if indeg0 else next(iter(node_ids))

        outputs: dict[str, dict[str, Any]] = {}
        trace: list[dict[str, Any]] = []
        visited: set[str] = set()

        # Simple queue: topological-ish execution; only execute when all upstream done
        ready = [entry]
        pending = set(node_ids)

        # Seed initial inputs at entry
        seed_inputs = dict(initial_inputs or {})

        while ready:
            nid = ready.pop(0)
            if nid in visited:
                continue
            n = node_by_id.get(nid)
            if not n:
                continue

            # Ensure all upstream nodes executed (except entry which can accept seed)
            upstream_edges = inc.get(nid, [])
            upstream_ids = [str(e.get("sourceNodeId") or "") for e in upstream_edges if e.get("sourceNodeId")]
            if nid != entry and any(uid and uid not in outputs for uid in upstream_ids):
                # Not ready yet; push back
                ready.append(nid)
                # Prevent infinite spin: if nothing can progress, break
                if all(
                    (x != entry and any(str(e.get("sourceNodeId") or "") not in outputs for e in inc.get(x, [])))
                    for x in ready
                ):
                    raise ValueError("存在无法满足依赖的节点（可能有断边/缺失输出）")
                continue

            node_type = str(n.get("type") or "").strip()
            config = dict(n.get("config") or {})
            display_label = str(n.get("label") or n.get("title") or "").strip()

            # Build inputs by merging upstream outputs
            upstream_payload: dict[str, Any] = {}
            texts: list[str] = []
            first_image_url = ""
            first_audio_url = ""
            first_video_url = ""
            media: list[dict[str, Any]] = []
            for e in upstream_edges:
                sid = str(e.get("sourceNodeId") or "")
                if not sid:
                    continue
                out_obj = outputs.get(sid)
                if out_obj is None:
                    continue
                upstream_payload[sid] = out_obj
                t = _as_text(out_obj).strip()
                if t:
                    texts.append(t)
                media.extend(_extract_media_items(out_obj, node_id=sid))
                # 尝试透传上游生成的图片 URL（若存在）
                if not first_image_url and isinstance(out_obj, dict):
                    cand = (
                        out_obj.get("generated_image_url")
                        or out_obj.get("image_url")
                        or out_obj.get("imageUrl")
                        or out_obj.get("url")
                    )
                    if cand:
                        first_image_url = str(cand).strip()
                if not first_audio_url and isinstance(out_obj, dict) and out_obj.get("audio_url"):
                    first_audio_url = str(out_obj.get("audio_url") or "").strip()
                if not first_video_url and isinstance(out_obj, dict) and out_obj.get("video_url"):
                    first_video_url = str(out_obj.get("video_url") or "").strip()

            inputs: dict[str, Any] = {"upstream": upstream_payload}
            if nid == entry and seed_inputs:
                inputs.update(seed_inputs)
                if "text" in seed_inputs and isinstance(seed_inputs["text"], str):
                    pass
            else:
                if texts:
                    inputs["text"] = "\n\n---\n\n".join(texts)
                else:
                    inputs["text"] = ""
                if media:
                    inputs["media"] = media
                if first_image_url and not inputs.get("image_url"):
                    inputs["image_url"] = first_image_url
                if first_audio_url and not inputs.get("audio_url"):
                    inputs["audio_url"] = first_audio_url
                if first_video_url and not inputs.get("video_url"):
                    inputs["video_url"] = first_video_url

            prov = str(config.get("provider") or "doubao").strip().lower()
            if prov in ("ark", "byte", "volcengine"):
                prov = "doubao"
            model_id = str(config.get("model") or "").strip()
            mroute = ""
            if node_type in ("chat", "ai_chat", "text", "image", "audio", "video"):
                mroute = prov if prov in ("doubao", "openai", "claude", "ollama", "vectorengine") else "doubao"
            activity = activity_for_canvas_node(
                node_type,
                display_title=display_label or nid,
                model_id=model_id,
                provider=prov,
                text_process_mode=str(config.get("processMode") or config.get("process_mode") or "llm"),
            )
            await emit.node_start(
                nid,
                title=display_label or nid,
                display_title=display_label or nid,
                node_type=node_type,
                model_route=mroute,
                activity=activity,
            )
            step = {
                "node": nid,
                "node_type": node_type,
                "inputs": inputs,
                "started_at": timezone.now().isoformat(),
                "activity": activity,
                "display_title": display_label,
            }

            try:
                # 执行节点
                out_obj = await asyncio.to_thread(
                    execute_canvas_node,
                    node_type=node_type,
                    config=config,
                    inputs=inputs,
                    user_id=user_id,
                    execution=execution,
                    client_node_id=nid,
                )
                out_obj = dict(out_obj)
                outputs[nid] = out_obj
                step["output"] = out_obj
                step["status"] = "completed"

                # 推送输出（用 token 事件承载，前端可复用现有渲染）
                preview = _as_text(out_obj).strip()
                if preview:
                    await emit.token(preview, nid)

                await emit.node_end(nid, "completed", activity=activity, title=display_label or nid, model_route=mroute)
            except Exception as exc:
                step["status"] = "failed"
                step["error"] = str(exc)
                await emit.workflow_error(f"node {nid} failed: {exc}")
                await emit.node_end(nid, "failed", activity=activity, title=display_label or nid, model_route=mroute)
                trace.append(step)
                raise

            trace.append(step)
            visited.add(nid)
            pending.discard(nid)

            # Enqueue downstream if all their upstream ready
            for e in out.get(nid, []):
                tid = str(e.get("targetNodeId") or "")
                if not tid or tid in visited:
                    continue
                # Only enqueue if all sources for tid are done (or it's entry)
                reqs = [str(x.get("sourceNodeId") or "") for x in inc.get(tid, [])]
                if all((r in outputs) for r in reqs if r):
                    ready.append(tid)

        # Final result: last executed node output or all outputs
        result = {
            "entry": entry,
            "outputs": outputs,
            "trace": trace,
        }

        await emit.workflow_end("completed", {"response": _as_text(outputs.get(list(outputs.keys())[-1], "")), "result": result})

        await _save_execution_completed(execution.pk, result)

    except Exception as exc:
        await _save_execution_failed(execution.pk, str(exc))
        await emit.workflow_error(str(exc))


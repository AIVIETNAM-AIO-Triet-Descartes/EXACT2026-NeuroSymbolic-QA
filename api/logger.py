# =============================================================================
# TODO — Danh sách log cần cài đặt trong toàn bộ pipeline
# Nguồn: DEMO_PLAN.md (Logging Setup) + SYSTEM.md §4.5
# Quy tắc: mọi node chỉ được dùng get_logger(__name__) từ file này,
#           KHÔNG tự cấu hình logging riêng.
# =============================================================================

# -----------------------------------------------------------------------------
# [TODO-LOG-1] api/main.py — logger.info() sau khi pipeline hoàn thành
# Gọi 1 lần duy nhất mỗi request, sau khi có solver_result và explanation.
# Bắt buộc có đủ 7 field sau (SYSTEM.md §4.5):
#
#   logger.info("request", extra={"extra": {
#       "question":           request.question[:80],  # truncate 80 ký tự
#       "query_type":         query_type,             # "type1" | "type2"
#       "answer":             solver_result["answer"],
#       "confidence":         solver_result["confidence"],
#       "solver_source":      solver_result["source"],  # "z3"|"sympy"|"llm_fallback"
#       "fol_retries":        state.get("fol_retries", 0),
#       "fallback_triggered": solver_result["source"] == "llm_fallback",
#   }})
#
# Nên thêm (input cho /exact-error-analysis, không bắt buộc trong 7 field):
#       "z3_timeout": True/False   — set True khi Z3 bị timeout
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-LOG-2] api/main.py — logger.error() trong except block của handle_query
# Gọi khi pipeline raise exception không bắt được ở các node bên trong.
# Message phải chứa traceback để debug được.
#
#   except Exception as e:
#       logger.error(f"Pipeline error: {e}", exc_info=True)
#       return QueryResponse(answer="Error", explanation=str(e))
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-LOG-3] pipeline/type1/z3_solver.py — logger.warning() khi Z3 timeout
# Gọi khi Z3 vượt quá 5s (SYSTEM.md §5 Fallback Strategy).
# Dùng để API Gateway set z3_timeout=True trong log chính [TODO-LOG-1].
#
#   logger.warning("Z3 timeout — switching to llm_fallback", extra={"extra": {
#       "z3_timeout": True,
#       "question_snippet": fol_list[:2],  # log vài FOL đầu để debug
#   }})
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-LOG-4] pipeline/type1/z3_solver.py — logger.warning() khi FOL parse fail
# Gọi khi Z3 không parse được FOL (trước khi trả SolverResult fallback).
#
#   logger.warning("FOL parse failed", extra={"extra": {
#       "fol_input": fol_list,
#       "error": str(e),
#   }})
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-LOG-5] pipeline/type2/sympy_solver.py — logger.warning() khi SymPy fail
# Gọi khi SymPy không giải được phương trình (SYSTEM.md §5 Fallback Strategy).
# Trigger confidence = 0.5, source = "llm_fallback".
#
#   logger.warning("SymPy solve failed — switching to llm_fallback", extra={"extra": {
#       "parsed_input": parsed,
#       "error": str(e),
#   }})
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-LOG-6] pipeline/type2/self_verifier.py — logger.warning() khi verify thất bại
# Gọi khi substitute ngược kết quả vào phương trình gốc không khớp (SYSTEM.md §5.1).
# Không block pipeline — chỉ giảm confidence xuống 0.4.
#
#   logger.warning("Self-verification failed", extra={"extra": {
#       "self_verify_failed": True,
#       "answer":   answer,
#       "expected": expected,
#       "computed": computed,
#   }})
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# [TODO-FIX] JSONFormatter hiện thiếu:
#   1. Field "ts" (timestamp ISO 8601 UTC) — bắt buộc theo DEMO_PLAN.md
#   2. Merge extra["extra"] vào log_obj để các field trên xuất hiện trong JSON
#   3. import datetime để tạo timestamp
#
# Spec từ DEMO_PLAN.md:
#   payload = {
#       "ts":     datetime.now(timezone.utc).isoformat(),
#       "level":  record.levelname,
#       "logger": record.name,
#       "msg":    record.getMessage(),
#   }
#   if hasattr(record, "extra"):
#       payload.update(record.extra)
# -----------------------------------------------------------------------------

import logging
import json


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_obj, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

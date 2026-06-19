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
from datetime import datetime, timezone
import sys
from typing import Literal
import contextvars
from loguru import logger as loguru_logger

# Context variable to hold logs for the current request
request_logs = contextvars.ContextVar("request_logs", default=None)

# Setup loguru sink to append to request_logs if active
def loguru_sink(message):
    logs_list = request_logs.get()
    if logs_list is not None:
        logs_list.append(str(message).strip())

loguru_logger.add(loguru_sink, level="DEBUG")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # 1. Khởi tạo cấu trúc JSON gốc chuẩn hệ thống
        log_obj = {
            "ts":     datetime.now(timezone.utc).isoformat(),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }

        # Các thuộc tính mặc định của hệ thống Python cần loại bỏ, chỉ giữ lại trường nghiệp vụ
        RESERVED_ATTRS = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "extra"
        }

        # 2. Quét toàn bộ mọi thuộc tính được truyền vào record (Chấp mọi kiểu viết extra)
        for key, value in record.__dict__.items():
            if key not in RESERVED_ATTRS:
                log_obj[key] = value

        # 3. Hỗ trợ xử lý nếu team viết lồng dạng extra={"extra": {...}} đúng theo Spec kế hoạch
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            if "extra" in record.extra and isinstance(record.extra["extra"], dict):
                log_obj.update(record.extra["extra"])
            else:
                log_obj.update(record.extra)

        # Xóa triệt để từ khóa phụ 'extra' nếu còn sót lại trong object
        log_obj.pop("extra", None)

        formatted_log = json.dumps(log_obj, ensure_ascii=False)
        
        # Capture standard log if active
        logs_list = request_logs.get()
        if logs_list is not None:
            logs_list.append(formatted_log)

        return formatted_log


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    logger.propagate = False  
    return logger


_request_logger = get_logger("pipeline_request")

def log_pipeline_request(
    question: str,
    query_type: Literal["type1", "type2"],
    answer: str,
    confidence: float,
    has_fol: bool,
    has_cot: bool,
    fol_retries: int,
    fallback_triggered: bool,
    z3_timeout: bool,
    solver_source: Literal["z3", "sympy", "llm_fallback"],
):
    """Hàm tiện ích ép buộc truyền đủ các trường nghiệp vụ khi kết thúc request"""
    _request_logger.info("request", extra={
        "extra": {
            "question":           question[:80],
            "query_type":         query_type,
            "answer":             answer,
            "confidence":         confidence,
            "has_fol":            has_fol,
            "has_cot":            has_cot,
            "fol_retries":        fol_retries,
            "fallback_triggered": fallback_triggered,
            "z3_timeout":         z3_timeout,
            "solver_source":      solver_source,
        }
    })


# ==========================================
# BỘ KIỂM THỬ NỘI BỘ (Chạy để xem kết quả)
# ==========================================
# =============================================================================
# BỘ KIỂM THỬ PHÂN TÍCH LỖI (Dành riêng cho Người số 5)
# =============================================================================
if __name__ == "__main__":
    print("=================== BẮT ĐẦU KIỂM THỬ ĐẦU RA LOGGER ===================")

    # -------------------------------------------------------------------------
    # CASE 1: Chạy qua hàm tiện ích do bạn viết (log_pipeline_request)
    # Tần suất: Gọi liên tục ở cuối mỗi request thành công tại api/main.py
    # -------------------------------------------------------------------------
    print("\n--- CASE 1: Gọi qua hàm tiện ích log_pipeline_request (Chuẩn Spec đầu ra phẳng) ---")
    log_pipeline_request(
        question="Calculate the total resistance of the parallel circuit.",
        query_type="type2",
        answer="6.67",
        confidence=1.0,
        has_fol=False,
        has_cot=True,
        fol_retries=0,
        fallback_triggered=False,
        z3_timeout=False,
        solver_source="sympy"
    )

    # -------------------------------------------------------------------------
    # CASE 2: Cách gọi viết lồng của team theo file kế hoạch ban đầu (DEMO_PLAN.md)
    # Tần suất: Rất dễ xảy ra nếu Lập trình viên copy nguyên si code mẫu từ file kế hoạch
    # -------------------------------------------------------------------------
    print("\n--- CASE 2: Thành viên khác gọi trực tiếp kiểu lồng extra={'extra': {...}} ---")
    logger_c2 = get_logger("pipeline.main_node")
    logger_c2.info("Yêu cầu xử lý thành công", extra={
        "extra": {
            "question":           "Socrates có chết không?",
            "query_type":         "type1",
            "answer":             "Đúng",
            "confidence":         1.0,
            "solver_source":      "z3",
            "fol_retries":        1,
            "fallback_triggered": False,
        }
    })

    # -------------------------------------------------------------------------
    # CASE 3: Cách gọi flat truyền thống của thư viện Python mặc định
    # Tần suất: Cực dễ xảy ra do thói quen gõ phím cũ của các kỹ sư trong dự án
    # -------------------------------------------------------------------------
    print("\n--- CASE 3: Thành viên khác gọi kiểu phẳng truyền thống extra={...} (Code cũ sẽ bị mất sạch dữ liệu) ---")
    logger_c3 = get_logger("pipeline.python_style")
    logger_c3.info("Xử lý nhanh bài toán", extra={
        "question":      "Calculate the force applied to the mass...",
        "query_type":    "type2",
        "answer":        "15.0",
        "solver_source": "sympy"
    })

    # -------------------------------------------------------------------------
    # CASE 4: Trường hợp siêu hiếm (Ca oái oăm: Vừa viết lồng vừa để flat bên ngoài)
    # Tần suất: Hiếm gặp, xuất hiện khi ráp nối code cũ và code mới lộn xộn
    # -------------------------------------------------------------------------
    print("\n--- CASE 4 (EDGE CASE): Truyền hỗn hợp vừa flat bên ngoài, vừa lồng bên trong 'extra' ---")
    logger_c4 = get_logger("pipeline.hybrid_style")
    logger_c4.info("Hỗn hợp dữ liệu", extra={
        "extra": {
            "query_type":  "type1",
            "fol_retries": 3
        },
        "answer":             "Sai",
        "confidence":         0.4,
        "solver_source":      "llm_fallback"
    })

    # -------------------------------------------------------------------------
    # CASE 5: Trường hợp phá hoại (Truyền sai kiểu dữ liệu, extra là một String chữ)
    # Tần suất: Hiếm gặp, do lập trình viên viết ẩu truyền sai định dạng biến
    # -------------------------------------------------------------------------
    print("\n--- CASE 5 (EDGE CASE): Truyền bậy biến extra thành một chuỗi String (Chống sập hệ thống) ---")
    logger_c5 = get_logger("pipeline.broken_style")
    logger_c5.info("Bắn log lỗi định dạng", extra="Đoạn chữ phá hoại hệ thống")

    print("\n========================= KẾT THÚC KIỂM THỬ =========================")
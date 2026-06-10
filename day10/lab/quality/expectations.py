"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    required_docs = {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
    present_docs = {r.get("doc_id") for r in cleaned_rows}
    missing_docs = sorted(required_docs - present_docs)
    ok7 = len(missing_docs) == 0
    results.append(
        ExpectationResult(
            "required_grading_doc_ids_present",
            ok7,
            "halt",
            f"missing_doc_ids={missing_docs}",
        )
    )

    access_l4 = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "access_control_sop"
        and "level 4 admin access" in (r.get("chunk_text") or "").lower()
        and (
            "it manager" in (r.get("chunk_text") or "").lower()
            or "ciso" in (r.get("chunk_text") or "").lower()
        )
    ]
    ok8 = len(access_l4) >= 1
    results.append(
        ExpectationResult(
            "access_control_l4_admin_approver_present",
            ok8,
            "halt",
            f"matching_chunks={len(access_l4)}",
        )
    )

    all_text = " ".join((r.get("chunk_text") or "") for r in cleaned_rows).lower()

    required_fact_groups = {
        "refund_7_working_days": ["7 ngày", "7 ngày làm việc"],
        "refund_excluded_digital_goods": ["hàng kỹ thuật số", "license key", "subscription"],
        "refund_finance_3_5_days": ["3-5 ngày làm việc", "3 đến 5 ngày"],
        "p1_initial_response_15m": ["15 phút", "15p"],
        "p1_resolution_4h": ["4 giờ", "4h"],
        "p1_auto_escalate_10m": ["10 phút"],
        "account_lock_5_attempts": ["5 lần"],
        "vpn_2_devices": ["2 thiết bị", "2 device"],
        "hr_12_annual_leave": ["12 ngày", "12 ngày phép năm"],
        "access_l4_approver": ["it manager", "ciso"],
    }

    missing_facts = []
    for fact_name, variants in required_fact_groups.items():
        if not any(v.lower() in all_text for v in variants):
            missing_facts.append(fact_name)

    ok9 = len(missing_facts) == 0
    results.append(
        ExpectationResult(
            "grading_core_facts_present",
            ok9,
            "halt",
            f"missing_facts={missing_facts}",
        )
    )

    p1_escalation_chunks = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "sla_p1_2026"
        and "ticket p1" in (r.get("chunk_text") or "").lower()
        and "auto escalate" in (r.get("chunk_text") or "").lower()
        and "không có phản hồi" in (r.get("chunk_text") or "").lower()
        and "10 phút" in (r.get("chunk_text") or "").lower()
    ]

    ok10 = len(p1_escalation_chunks) >= 1
    results.append(
        ExpectationResult(
            "sla_p1_auto_escalation_10m_canonical_present",
            ok10,
            "halt",
            f"matching_chunks={len(p1_escalation_chunks)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt

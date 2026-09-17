#!/usr/bin/env python3
"""
Legal Engine: Generates formal legal violation notices and statutory
infraction reports under Vietnamese Tourism and Consumer Protection Law.
"""

from typing import Dict, Optional

class LegalEngine:
    @staticmethod
    def generate_legal_notice(audit_result: Dict) -> Dict:
        """
        Generate statutory citations, penalty liability, and formal notice text
        for a given audit result.
        """
        status = audit_result["status"]
        inp = audit_result["input"]
        hotel_name = inp.get("name", "Unknown Property")
        claimed_stars = inp.get("claimed_stars", 0)
        ota_source = inp.get("ota_source", "OTA")
        ota_url = inp.get("ota_url", "")
        official = audit_result.get("official_record")

        if status == "VERIFIED_LEGITIMATE":
            return {
                "is_violation": False,
                "summary": "Full Statutory Compliance",
                "citations": [
                    "Luật Du lịch 2017 (Law No. 09/2017/QH14) - Điều 50",
                    "TCVN 4391:2015 - Tiêu chuẩn quốc gia về Khách sạn"
                ],
                "details": f"Property is officially accredited as {official['stars']}-Star by the Vietnam National Authority of Tourism (VNAT)."
            }

        # Build Infraction Dossier
        violations = []
        penalties = []

        # Violation 1: False or unauthorized star rating
        violations.append({
            "law": "Luật Du lịch 2017 (Law No. 09/2017/QH14) - Điều 9, Khoản 8",
            "statute_title": "Các hành vi bị nghiêm cấm trong hoạt động du lịch",
            "text": "Nghiêm cấm hành vi quảng cáo không đúng loại, hạng cơ sở lưu trú du lịch đã được cơ quan nhà nước có thẩm quyền công nhận; hoặc quảng cáo về loại, hạng khi chưa được cơ quan nhà nước có thẩm quyền công nhận.",
            "application": f"The listing on {ota_source} displays {claimed_stars} stars without corresponding accreditation by VNAT."
        })

        # Violation 2: Central Authority Exclusive Jurisdiction
        violations.append({
            "law": "Luật Du lịch 2017 - Điều 50, Khoản 3",
            "statute_title": "Thẩm quyền công nhận hạng cơ sở lưu trú du lịch",
            "text": "Cục Du lịch Quốc gia Việt Nam (Tổng cục Du lịch) là cơ quan duy nhất có thẩm quyền thẩm định, công nhận cơ sở lưu trú du lịch hạng 4 sao và hạng 5 sao trên toàn quốc.",
            "application": "OTAs and property operators cannot self-declare or algorithmically grant 4-star or 5-star status."
        })

        # Violation 3: Consumer Protection Law (Deceptive Practice)
        violations.append({
            "law": "Luật Bảo vệ quyền lợi người tiêu dùng 2023 - Điều 10 & Điều 39",
            "statute_title": "Hành vi bị cấm & Trách nhiệm của tổ chức thiết lập nền tảng số trung gian",
            "text": "Cấm hành vi lừa dối, gây nhầm lẫn cho người tiêu dùng thông qua việc cung cấp thông tin sai lệch về tiêu chuẩn, chất lượng, quy cách sản phẩm, dịch vụ. Nền tảng số trung gian có nghĩa vụ xác minh thông tin và liên đới chịu trách nhiệm nếu hiển thị thông tin gian dối.",
            "application": f"{ota_source} renders gold star iconography ({'★' * claimed_stars}) inducing travelers into booking under false quality expectations."
        })

        # Physical Standard Violation if hostel/bunk bed
        if status == "BLATANT_HOSTEL_FRAUD":
            violations.append({
                "law": "Tiêu chuẩn Quốc gia TCVN 4391:2015 - Tiêu chuẩn Xếp hạng Khách sạn",
                "statute_title": "Quy chuẩn cơ sở vật chất tối thiểu cho Khách sạn 4 sao và 5 sao",
                "text": "Quy định quy mô buồng phòng tối thiểu: 80 phòng đối với hạng 4 sao, 100 phòng đối với hạng 5 sao; cấm hoàn toàn bố trí giường tầng/phòng ngủ tập thể (dormitory) trong buồng lưu trú.",
                "application": "This establishment features dormitory/bunk beds or inadequate room count, making 4-star or 5-star qualification physically and legally impossible."
            })

        # Monetary and Administrative Liabilities
        penalties.append("Decree 38/2021/NĐ-CP: Fines of up to 160,000,000 VND for false and deceptive commercial advertising.")
        penalties.append("Decree 45/2019/NĐ-CP (amended by Decree 129/2021/NĐ-CP): Compulsory immediate dismantling and removal of all unauthorized star signage and digital listings.")
        penalties.append("Decree 85/2021/NĐ-CP: Potential suspension of cross-border e-commerce operation rights in Vietnam for repeated consumer protection violations.")

        formal_letter = f"""
================================================================================
FORMAL STATUTORY NOTICE OF FALSE HOTEL STAR CLASSIFICATION
Under the Authority of the Law on Tourism 2017 & Law on Consumer Protection 2023
================================================================================

TARGET LISTING:
  Property:        {hotel_name}
  Platform:        {ota_source}
  Claimed Rating:  {claimed_stars} Stars ({'★' * claimed_stars})
  URL:             {ota_url or 'N/A'}

LEGAL FINDINGS:
  Audit Status:    {status}
  Severity Level:  {audit_result['severity']}
  Summary:         {audit_result['message']}

STATUTORY BREACHES:
  1. Breach of Article 9, Clause 8, Law on Tourism 2017:
     Unauthorized marketing and public display of an unaccredited star rating.
  2. Breach of Article 50, Law on Tourism 2017:
     Circumvention of VNAT exclusive statutory certification monopoly.
  3. Breach of Articles 10 & 39, Law on Protection of Consumer Rights 2023:
     Misleading digital representations to international and domestic travelers.

REMEDIAL ACTION REQUIRED:
  Immediate removal of the {claimed_stars}-star designation from {ota_source}
  or replacement with 'Unranked Property / Backpacker Accommodation'.
================================================================================
"""

        return {
            "is_violation": True,
            "status": status,
            "severity": audit_result["severity"],
            "summary": audit_result["message"],
            "statutory_violations": violations,
            "penalties": penalties,
            "formal_notice_text": formal_letter.strip()
        }

if __name__ == "__main__":
    test_audit = {
        "status": "BLATANT_HOSTEL_FRAUD",
        "severity": "CRITICAL",
        "message": "Backpacker hostel falsely sporting 5 stars on Agoda. Offers bunk beds in shared dorms.",
        "input": {
            "name": "Hanoi Old Quarter Backpacker Oasis",
            "claimed_stars": 5,
            "ota_source": "Agoda",
            "ota_url": "https://www.agoda.com/hanoi-old-quarter-backpacker-oasis/hotel/hanoi-vn.html"
        }
    }
    notice = LegalEngine.generate_legal_notice(test_audit)
    print(notice["formal_notice_text"])

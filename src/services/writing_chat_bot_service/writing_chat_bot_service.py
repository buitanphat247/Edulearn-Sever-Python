import os
import requests
import json
import re
import uuid
import random
from typing import Dict, Optional, List

# LM Studio API endpoint (có thể config qua env)
LM_STUDIO_BASE_URL = os.getenv('LM_STUDIO_URL', 'http://192.168.183.1:1234')
LM_STUDIO_API_URL = f"{LM_STUDIO_BASE_URL}/v1/chat/completions"

# Global session for reused connections (Speed optimization)
session = requests.Session()

# ============================================================================
# HƯỚNG DẪN BẬT GPU ĐỂ TĂNG TỐC ĐỘ (QUAN TRỌNG!)
# ============================================================================
# GPU nhanh hơn CPU 5-10 lần. BẮT BUỘC bật trong LM Studio:
#
# 1. Mở LM Studio
# 2. Vào Settings → Hardware
# 3. Chọn GPU Acceleration:
#    - NVIDIA: Chọn "CUDA" và set GPU Layers = Max (hoặc Auto)
#    - AMD: Chọn "ROCm" (nếu hỗ trợ)
#    - Mac: Chọn "Metal" và set GPU Layers = Max
# 4. Kiểm tra log trong LM Studio:
#    - Nếu thấy "Running on CPU" → CHƯA bật GPU
#    - Nếu thấy "Using GPU" hoặc "CUDA" → Đã bật thành công
#
# 5. Model khuyến nghị cho GPU:
#    - NVIDIA GTX/RTX: Dùng model 7B-13B với Q4
#    - NVIDIA RTX 3060+ (8GB+): Có thể dùng 13B Q4
#    - NVIDIA RTX 4090: Có thể dùng 20B+ Q4
#    - Model nhẹ: phi-3-mini, qwen2.5-3b, llama-3.2-3b (Q4)
#
# 6. Nếu không có GPU hoặc GPU yếu:
#    - Dùng model nhỏ hơn (3B với Q4)
#    - Giảm max_tokens trong code
#    - Tăng timeout
# ============================================================================

# Topic mapping với mô tả tiếng Việt để AI hiểu rõ hơn
TOPIC_MAPPING = {
    # Cơ bản (General)
    "greetings": "Chào hỏi và làm quen",
    "self_introduction": "Giới thiệu bản thân",
    "daily_conversation": "Trò chuyện hằng ngày",
    "weather_talk": "Nói về thời tiết",
    "family_friends": "Gia đình và bạn bè",
    "weekend_plans": "Kế hoạch cuối tuần",
    # Trung bình (General)
    "shopping": "Mua sắm và thanh toán",
    "restaurant": "Đặt món và nhà hàng",
    "transportation": "Phương tiện và di chuyển",
    "asking_directions": "Hỏi đường và chỉ đường",
    "hotel_booking": "Đặt phòng khách sạn",
    "doctor_visit": "Khám bác sĩ và sức khỏe",
    "phone_calls": "Cuộc gọi điện thoại",
    "making_friends": "Kết bạn và giao lưu",
    "invitations": "Mời và nhận lời mời",
    "hobbies_sports": "Sở thích và thể thao",
    "entertainment": "Giải trí và phim ảnh",
    "food_preferences": "Sở thích ẩm thực",
    "small_talk": "Trò chuyện phím",
    # Nâng cao (General)
    "travel_planning": "Lên kế hoạch du lịch",
    "airport_customs": "Sân bay và hải quan",
    "emergencies": "Tình huống khẩn cấp",
    "expressing_opinions": "Bày tỏ ý kiến",
    "complaining_suggesting": "Phàn nàn và gợi ý",
    "cultural_differences": "Khác biệt văn hóa",
    "problem_solving": "Giải quyết vấn đề",
    # Trung bình (IELTS)
    "university_life": "Cuộc sống đại học",
    "study_methods": "Phương pháp học tập",
    "online_learning": "Học trực tuyến",
    "remote_work": "Làm việc từ xa",
    "sustainable_living": "Lối sống bền vững",
    "healthy_lifestyle": "Lối sống lành mạnh",
    "work_life_balance": "Cân bằng công việc - cuộc sống",
    "consumer_culture": "Văn hóa tiêu dùng",
    "arts_education": "Giáo dục nghệ thuật",
    "tourism_impact": "Tác động du lịch",
    # Nâng cao (IELTS)
    "education_system": "Hệ thống giáo dục",
    "education_technology": "Công nghệ trong giáo dục",
    "childhood_education": "Giáo dục trẻ em",
    "higher_education": "Giáo dục đại học",
    "social_media_impact": "Tác động mạng xã hội",
    "artificial_intelligence": "Trí tuệ nhân tạo",
    "digital_privacy": "Quyền riêng tư số",
    "technology_addiction": "Nghiện công nghệ",
    "automation_jobs": "Tự động hóa và việc làm",
    "climate_change": "Biến đổi khí hậu",
    "renewable_energy": "Năng lượng tái tạo",
    "pollution_solutions": "Ô nhiễm và giải pháp",
    "conservation_efforts": "Nỗ lực bảo tồn",
    "urban_planning": "Quy hoạch đô thị",
    "mental_health": "Sức khỏe tinh thần",
    "healthcare_systems": "Hệ thống y tế",
    "aging_population": "Dân số già hóa",
    "income_inequality": "Bất bình đẳng thu nhập",
    "globalization": "Toàn cầu hóa",
    "traditional_vs_modern": "Truyền thống vs hiện đại",
    "government_policies": "Chính sách chính phủ",
    "cultural_preservation": "Bảo tồn văn hóa",
    "media_influence": "Ảnh hưởng của truyền thông",
    # Trung bình (Công việc)
    "job_interviews": "Phỏng vấn xin việc",
    "email_etiquette": "Nghi thức email",
    "team_collaboration": "Hợp tác nhóm",
    "career_planning": "Lập kế hoạch sự nghiệp",
    "skill_development": "Phát triển kỹ năng",
    "workplace_learning": "Học tập tại nơi làm việc",
    "professional_goals": "Mục tiêu nghề nghiệp",
    # Nâng cao (Công việc)
    "networking_events": "Sự kiện kết nối",
    "meeting_presentations": "Họp và thuyết trình",
    "performance_reviews": "Đánh giá hiệu suất",
    "project_management": "Quản lý dự án",
    "client_relations": "Quan hệ khách hàng",
    "negotiation_skills": "Kỹ năng đàm phán",
    "problem_solving_work": "Giải quyết vấn đề công việc",
    "leadership_styles": "Phong cách lãnh đạo",
    "employee_motivation": "Động lực nhân viên",
    "conflict_resolution": "Giải quyết xung đột",
    "change_management": "Quản lý thay đổi",
    "delegation_skills": "Kỹ năng phân công",
    "career_transitions": "Chuyển đổi nghề nghiệp",
    "tech_innovation": "Đổi mới công nghệ",
    "financial_planning": "Lập kế hoạch tài chính",
    "marketing_strategies": "Chiến lược marketing",
    "supply_chain": "Chuỗi cung ứng",
    "quality_assurance": "Đảm bảo chất lượng"
}

# Topic categories để trả về theo nhóm
TOPIC_CATEGORIES = {
    "general": {
        "🌱 Cơ bản": [
            {"value": "greetings", "label": "Chào hỏi và làm quen"},
            {"value": "self_introduction", "label": "Giới thiệu bản thân"},
            {"value": "daily_conversation", "label": "Trò chuyện hằng ngày"},
            {"value": "weather_talk", "label": "Nói về thời tiết"},
            {"value": "family_friends", "label": "Gia đình và bạn bè"},
            {"value": "weekend_plans", "label": "Kế hoạch cuối tuần"}
        ],
        "🌿 Trung bình": [
            {"value": "shopping", "label": "Mua sắm và thanh toán"},
            {"value": "restaurant", "label": "Đặt món và nhà hàng"},
            {"value": "transportation", "label": "Phương tiện và di chuyển"},
            {"value": "asking_directions", "label": "Hỏi đường và chỉ đường"},
            {"value": "hotel_booking", "label": "Đặt phòng khách sạn"},
            {"value": "doctor_visit", "label": "Khám bác sĩ và sức khỏe"},
            {"value": "phone_calls", "label": "Cuộc gọi điện thoại"},
            {"value": "making_friends", "label": "Kết bạn và giao lưu"},
            {"value": "invitations", "label": "Mời và nhận lời mời"},
            {"value": "hobbies_sports", "label": "Sở thích và thể thao"},
            {"value": "entertainment", "label": "Giải trí và phim ảnh"},
            {"value": "food_preferences", "label": "Sở thích ẩm thực"},
            {"value": "small_talk", "label": "Trò chuyện phím"}
        ],
        "🎯 Nâng cao": [
            {"value": "travel_planning", "label": "Lên kế hoạch du lịch"},
            {"value": "airport_customs", "label": "Sân bay và hải quan"},
            {"value": "emergencies", "label": "Tình huống khẩn cấp"},
            {"value": "expressing_opinions", "label": "Bày tỏ ý kiến"},
            {"value": "complaining_suggesting", "label": "Phàn nàn và gợi ý"},
            {"value": "cultural_differences", "label": "Khác biệt văn hóa"},
            {"value": "problem_solving", "label": "Giải quyết vấn đề"}
        ]
    },
    "ielts": {
        "🌿 Trung bình": [
            {"value": "university_life", "label": "Cuộc sống đại học"},
            {"value": "study_methods", "label": "Phương pháp học tập"},
            {"value": "online_learning", "label": "Học trực tuyến"},
            {"value": "remote_work", "label": "Làm việc từ xa"},
            {"value": "sustainable_living", "label": "Lối sống bền vững"},
            {"value": "healthy_lifestyle", "label": "Lối sống lành mạnh"},
            {"value": "work_life_balance", "label": "Cân bằng công việc - cuộc sống"},
            {"value": "consumer_culture", "label": "Văn hóa tiêu dùng"},
            {"value": "arts_education", "label": "Giáo dục nghệ thuật"},
            {"value": "tourism_impact", "label": "Tác động du lịch"}
        ],
        "🎯 Nâng cao": [
            {"value": "education_system", "label": "Hệ thống giáo dục"},
            {"value": "education_technology", "label": "Công nghệ trong giáo dục"},
            {"value": "childhood_education", "label": "Giáo dục trẻ em"},
            {"value": "higher_education", "label": "Giáo dục đại học"},
            {"value": "social_media_impact", "label": "Tác động mạng xã hội"},
            {"value": "artificial_intelligence", "label": "Trí tuệ nhân tạo"},
            {"value": "digital_privacy", "label": "Quyền riêng tư số"},
            {"value": "technology_addiction", "label": "Nghiện công nghệ"},
            {"value": "automation_jobs", "label": "Tự động hóa và việc làm"},
            {"value": "climate_change", "label": "Biến đổi khí hậu"},
            {"value": "renewable_energy", "label": "Năng lượng tái tạo"},
            {"value": "pollution_solutions", "label": "Ô nhiễm và giải pháp"},
            {"value": "conservation_efforts", "label": "Nỗ lực bảo tồn"},
            {"value": "urban_planning", "label": "Quy hoạch đô thị"},
            {"value": "mental_health", "label": "Sức khỏe tinh thần"},
            {"value": "healthcare_systems", "label": "Hệ thống y tế"},
            {"value": "aging_population", "label": "Dân số già hóa"},
            {"value": "income_inequality", "label": "Bất bình đẳng thu nhập"},
            {"value": "globalization", "label": "Toàn cầu hóa"},
            {"value": "traditional_vs_modern", "label": "Truyền thống vs hiện đại"},
            {"value": "government_policies", "label": "Chính sách chính phủ"},
            {"value": "cultural_preservation", "label": "Bảo tồn văn hóa"},
            {"value": "media_influence", "label": "Ảnh hưởng của truyền thông"}
        ]
    },
    "work": {
        "🌿 Trung bình": [
            {"value": "job_interviews", "label": "Phỏng vấn xin việc"},
            {"value": "email_etiquette", "label": "Nghi thức email"},
            {"value": "team_collaboration", "label": "Hợp tác nhóm"},
            {"value": "career_planning", "label": "Lập kế hoạch sự nghiệp"},
            {"value": "skill_development", "label": "Phát triển kỹ năng"},
            {"value": "workplace_learning", "label": "Học tập tại nơi làm việc"},
            {"value": "professional_goals", "label": "Mục tiêu nghề nghiệp"}
        ],
        "🎯 Nâng cao": [
            {"value": "networking_events", "label": "Sự kiện kết nối"},
            {"value": "meeting_presentations", "label": "Họp và thuyết trình"},
            {"value": "performance_reviews", "label": "Đánh giá hiệu suất"},
            {"value": "project_management", "label": "Quản lý dự án"},
            {"value": "client_relations", "label": "Quan hệ khách hàng"},
            {"value": "negotiation_skills", "label": "Kỹ năng đàm phán"},
            {"value": "problem_solving_work", "label": "Giải quyết vấn đề công việc"},
            {"value": "leadership_styles", "label": "Phong cách lãnh đạo"},
            {"value": "employee_motivation", "label": "Động lực nhân viên"},
            {"value": "conflict_resolution", "label": "Giải quyết xung đột"},
            {"value": "change_management", "label": "Quản lý thay đổi"},
            {"value": "delegation_skills", "label": "Kỹ năng phân công"},
            {"value": "career_transitions", "label": "Chuyển đổi nghề nghiệp"},
            {"value": "tech_innovation", "label": "Đổi mới công nghệ"},
            {"value": "financial_planning", "label": "Lập kế hoạch tài chính"},
            {"value": "marketing_strategies", "label": "Chiến lược marketing"},
            {"value": "supply_chain", "label": "Chuỗi cung ứng"},
            {"value": "quality_assurance", "label": "Đảm bảo chất lượng"}
        ]
    }
}

def build_prompt(
    language: str,
    topic: str,
    difficulty: int,
    custom_topic: bool,
    custom_topic_text: str,
    content_type: str,
    learning_purpose: str
) -> str:
    """
    Xây dựng prompt tối ưu để gửi lên AI model.
    """
    # Xác định ngôn ngữ target
    is_vietnamese = language.lower() in ['vietnamese', 'vi', 'tiếng việt', 'tieng viet']
    
    # Xác định chủ đề thực tế
    if custom_topic and custom_topic_text:
        actual_topic = custom_topic_text
    elif topic in TOPIC_MAPPING:
        # Sử dụng mô tả tiếng Việt từ mapping để AI hiểu rõ hơn
        actual_topic = TOPIC_MAPPING[topic]
    else:
        actual_topic = topic
    
    # Map difficulty level
    difficulty_map = {
        1: "beginner" if not is_vietnamese else "sơ cấp",
        2: "basic-intermediate" if not is_vietnamese else "cơ bản-trung cấp",
        3: "intermediate" if not is_vietnamese else "trung cấp",
        4: "intermediate-advanced" if not is_vietnamese else "trung cấp-cao cấp",
        5: "advanced" if not is_vietnamese else "cao cấp"
    }
    difficulty_text = difficulty_map.get(difficulty, difficulty_map[2])
    
    # Map content type
    content_type_map = {
        "DIALOGUE": "dialogue" if not is_vietnamese else "hội thoại",
        "ESSAY": "essay" if not is_vietnamese else "bài luận",
        "STORY": "story" if not is_vietnamese else "câu chuyện"
    }
    content_type_text = content_type_map.get(content_type, "dialogue")
    
    # Map learning purpose
    purpose_map = {
        "COMMUNICATION": "communication" if not is_vietnamese else "giao tiếp",
        "GRAMMAR": "grammar" if not is_vietnamese else "ngữ pháp",
        "VOCABULARY": "vocabulary" if not is_vietnamese else "từ vựng"
    }
    purpose_text = purpose_map.get(learning_purpose, "communication")
    
    # Số lượt hội thoại: Tối thiểu 12, tối đa 15 câu
    # Random trong khoảng 12-15 để có sự đa dạng
    turns_count = random.randint(12, 15)
    
    # TỐI ƯU PROMPT: Ngắn gọn, rõ ràng, yêu cầu song ngữ để check đáp án
    # YÊU CẦU: Câu NGẮN GỌN, TỰ NHIÊN như hội thoại thực tế (không quá dài)
    if is_vietnamese:
        prompt = f"""Bạn là trợ lý ảo tạo nội dung học tập chuyên nghiệp.
 Nhiệm vụ: Tạo {content_type_text} (tối thiểu 12, tối đa {turns_count} lượt) để luyện {language}.
 Chủ đề: {actual_topic}
 Trình độ: {difficulty_text} ({difficulty}/5) - Mục đích: {purpose_text}

 QUY ĐỊNH BẮT BUỘC (KHÔNG ĐƯỢC SAI):
 1. Format từng dòng: "Tên: Câu Tiếng Việt | Dịch Tiếng Anh"
 2. KHÔNG đánh số, KHÔNG dòng trống thừa.
 3. Số lượng: Tối thiểu 12 câu, tối đa {turns_count} câu (ưu tiên {turns_count} câu).
 4. Nội dung TỰ NHIÊN, ĐỦ DÀI như hội thoại thực tế:
    - Mỗi câu PHẢI có ít nhất 15-20 từ (không tính tên người nói)
    - Câu đầy đủ, chi tiết, có ngữ cảnh rõ ràng, thông tin phong phú
    - Thêm chi tiết về tình huống, lý do, cảm xúc để câu dài hơn
    - Giống như người thật nói chuyện với nhau (không phải câu ngắn cụt lủn)
    - TRÁNH câu quá ngắn (dưới 15 từ) - đây là lỗi nghiêm trọng
    - Tự nhiên, thoải mái, nhưng phải đủ dài và chi tiết
 5. Phải có dấu gạch đứng "|" phân cách.
 6. Mỗi lượt hội thoại phải có nội dung phù hợp, không lặp lại.

 Mẫu (câu 15-20 từ, TỰ NHIÊN và ĐỦ DÀI):
 Lan: Chào Minh, dạo này công việc của bạn thế nào rồi? Mình thấy bạn bận rộn lắm. | Hello Minh, how has your work been lately? I noticed you've been very busy.
 Minh: Ổn cả Lan ạ, mình vừa được giao một dự án mới liên quan đến trí tuệ nhân tạo và đang học hỏi thêm nhiều kiến thức mới. | It's all good, Lan. I just got assigned a new project related to artificial intelligence and I'm learning a lot of new knowledge.
 Lan: Ồ, nghe thú vị đấy! Cụ thể là dự án gì vậy bạn? Mình cũng quan tâm đến lĩnh vực này. | Oh, that sounds interesting! What exactly is the project? I'm also interested in this field.

 BẮT ĐẦU NGAY - TẠO TỐI THIỂU 12, TỐI ĐA {turns_count} CÂU, MỖI CÂU PHẢI CÓ ÍT NHẤT 15-20 TỪ:"""
    else:
        prompt = f"""You are a professional language learning content creator.
 Task: Create a {content_type_text} (minimum 12, maximum {turns_count} turns) for {language} practice.
 Topic: {actual_topic}
 Level: {difficulty_text} ({difficulty}/5) - Goal: {purpose_text}

 STRICT MANDATORY RULES:
 1. Format each line exactly as: "Speaker: Content in Vietnamese | Content in English"
 2. NO numbering, NO extra empty lines.
 3. Quantity: Minimum 12 sentences, maximum {turns_count} sentences (prefer {turns_count} sentences).
 4. Sentences MUST BE NATURAL, LONG ENOUGH, LIKE REAL CONVERSATIONS:
    - Each sentence MUST have at least 15-20 words (excluding speaker name)
    - Complete, detailed sentences with rich context and information
    - Add details about situations, reasons, emotions to make sentences longer
    - Like real people talking to each other (not short, abrupt sentences)
    - AVOID sentences that are too short (under 15 words) - this is a serious error
    - Natural, relaxed, but must be long enough and detailed
 5. MUST use vertical bar "|" as separator.
 6. Each turn must have appropriate content, no repetition.

 Example (15-20 words, NATURAL and LONG ENOUGH):
 Lan: Chào Minh, dạo này công việc của bạn thế nào rồi? Mình thấy bạn bận rộn lắm. | Hello Minh, how has your work been lately? I noticed you've been very busy.
 Minh: Ổn cả Lan ạ, mình vừa được giao một dự án mới liên quan đến trí tuệ nhân tạo và đang học hỏi thêm nhiều kiến thức mới. | It's all good, Lan. I just got assigned a new project related to artificial intelligence and I'm learning a lot of new knowledge.
 Lan: Ồ, nghe thú vị đấy! Cụ thể là dự án gì vậy bạn? Mình cũng quan tâm đến lĩnh vực này. | Oh, that sounds interesting! What exactly is the project? I'm also interested in this field.

 BEGIN IMMEDIATELY - CREATE MINIMUM 12, MAXIMUM {turns_count} SENTENCES, EACH MUST HAVE AT LEAST 15-20 WORDS:"""
    
    return prompt


def parse_dialogue_to_parallel_sentences(dialogue: str) -> tuple[List[str], List[str]]:
    """
    Parse dialogue song ngữ thành 2 mảng: Target và Native (Translation).
    Format: Speaker: Content | Translation
    """
    if not dialogue:
        return [], []
    
    target_sentences = []
    translation_sentences = []
    
    lines = dialogue.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Format chuẩn: "Speaker: Content | Translation"
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                target_part = parts[0].strip() # "Speaker: Content"
                trans_part = parts[1].strip()  # "Translation"
                
                # Logic xử lý nếu AI lỡ thêm "Meaning:" hay "Translation:" vào đầu
                # Chỉ xử lý nếu có prefix rõ ràng (ví dụ có dấu :)
                if ':' in trans_part:
                    # Nếu format là "Meaning: Xin chào" thì bỏ "Meaning:"
                    # Nếu format là "Speaker: Xin chào" thì cũng có thể bỏ Speaker nếu muốn
                    # Nhưng để an toàn và đơn giản, ta giữ nguyên nội dung bản dịch
                    # Trừ khi nó quá dài dòng.
                    # Ở đây ta ưu tiên lấy nội dung sau dấu : cuối cùng hoặc đầu tiên?
                    # Prompt example: "A: Hello | Xin chào" -> Không có :
                    pass

                target_sentences.append(target_part)
                
                # Tự động thêm Speaker cho phần Translation để người dùng biết ai đang nói
                # target_part format: "Speaker: Content"
                if ':' in target_part:
                    speaker_name = target_part.split(':', 1)[0].strip()
                    # Chỉ thêm nếu trans_part chưa có speaker đó
                    if not trans_part.startswith(speaker_name):
                        trans_part = f"{speaker_name}: {trans_part}"
                
                translation_sentences.append(trans_part)
                
        elif ':' in line:
            # Fallback: cố gắng cứu dữ liệu nếu thiếu |
            target_sentences.append(line)
            # Nếu dòng có format "A: Content", ta cứ coi như là Target
            # Translation để trống vì không parse được
            translation_sentences.append("")
            
    return target_sentences, translation_sentences


def generate_dialogue(
    language: str,
    topic: str,
    difficulty: int,
    custom_topic: bool = False,
    custom_topic_text: str = "",
    content_type: str = "DIALOGUE",
    learning_purpose: str = "COMMUNICATION",
    mode: str = "AI_GENERATED"
) -> Dict:
    """
    Gọi LM Studio API để tạo dialogue/nội dung writing.
    """
    try:
        # Xây dựng prompt tối ưu
        prompt = build_prompt(
            language=language,
            topic=topic,
            difficulty=difficulty,
            custom_topic=custom_topic,
            custom_topic_text=custom_topic_text,
            content_type=content_type,
            learning_purpose=learning_purpose
        )
        
        # Tối ưu token count - Với 12-15 câu, mỗi câu 15-20 từ + translation
        # Mỗi câu: 15-20 từ (VN) + 15-20 từ (EN) = ~30-40 từ/câu = ~45-60 tokens/câu
        # Tổng: 15 câu × 52 tokens = ~780 tokens, nhưng cần buffer cho format
        max_tokens_map = {
            1: 1000,  # Beginner: 12-15 câu dài (~800 tokens)
            2: 1100,  # Basic-intermediate: 12-15 câu (~900 tokens)
            3: 1200,  # Intermediate: 12-15 câu (~1000 tokens)
            4: 1300,  # Intermediate-advanced: 12-15 câu (~1100 tokens)
            5: 1400   # Advanced: 12-15 câu có thể dài hơn một chút (~1200 tokens)
        }
        max_tokens = max_tokens_map.get(difficulty, 1100)
        
        # OpenAI Configuration
        # Lấy API Key từ biến môi trường (BẮT BUỘC)
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
             return {'error': 'OpenAI API Key is missing. Please set OPENAI_API_KEY env var.'}
             
        openai_api_url = "https://api.openai.com/v1/chat/completions"
        model_name = "gpt-3.5-turbo" # Sử dụng model nhanh & rẻ của OpenAI
        
        # Payload chuẩn OpenAI
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "Format: 'Speaker: Content | Translation'."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Gọi API OpenAI
        response = session.post(
            openai_api_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_api_key}"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {'error': f'OpenAI API error: {response.status_code} - {response.text}'}
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            dialogue = result['choices'][0]['message']['content'].strip()
            
            # Parse thành 2 list song song
            target_sents, trans_sents = parse_dialogue_to_parallel_sentences(dialogue)
            
            return {
                'dialogue': dialogue,
                'target_sentences': target_sents,
                'translation_sentences': trans_sents,
                'error': None
            }
        else:
            return {'error': 'Invalid response format'}
            
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def generate_suggestion(
    original_sentence: str,
    target_language: str = "English"
) -> Dict:
    """
    Tạo gợi ý (hint) cho người dùng khi họ gặp khó khăn.
    Gợi ý có thể là từ vựng khó, cấu trúc ngữ pháp, hoặc gợi ý dịch nghĩa.
    """
    try:
        # Check API Key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
             return {'error': 'OpenAI API Key is missing.'}
             
        openai_api_url = "https://api.openai.com/v1/chat/completions"
        model_name = "gpt-3.5-turbo"
        
        # Xác định ngôn ngữ nguồn (source) và đích (target)
        is_target_english = target_language.lower() in ['english', 'en']
        
        prompt = f"""You are a helpful language tutor.
Task: Analyze the following sentence and provide vocabulary hints and grammar structure for translation into {target_language}.

Input Sentence: "{original_sentence}"

REQUIREMENTS - Return ONLY valid JSON (no explanations, no markdown):
1. Extract 3-5 key vocabulary words/phrases from the sentence
2. For each word: provide the word in {target_language} and its meaning in Vietnamese
3. Describe the grammar structure used in the sentence (in Vietnamese)
4. Do NOT provide the full translation

JSON Format (MUST follow exactly):
{{
    "vocabulary": [
        {{"word": "word in {target_language}", "meaning": "nghĩa tiếng Việt"}},
        {{"word": "another word", "meaning": "nghĩa khác"}}
    ],
    "structure": "Mô tả cấu trúc ngữ pháp bằng tiếng Việt (ví dụ: Câu hỏi trực tiếp, sử dụng thì hiện tại đơn...)"
}}

Return JSON only:"""

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Giảm để output nhất quán hơn cho JSON
            "max_tokens": 300  # Tăng để đủ cho JSON response
        }
        
        # Use existing session
        response = session.post(
            openai_api_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_api_key}"
            },
            timeout=30
        )
        
        if response.status_code != 200:
             return {'error': f'OpenAI API error: {response.status_code}'}
             
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content'].strip()
            
            # Parse JSON từ response
            try:
                # Loại bỏ markdown code blocks nếu có
                if content.startswith('```'):
                    # Tìm và extract JSON từ code block
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                    else:
                        # Nếu không match, thử lấy phần giữa ```
                        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL).strip()
                
                # Parse JSON
                suggestion_data = json.loads(content)
                
                # Validate structure
                if 'vocabulary' not in suggestion_data or 'structure' not in suggestion_data:
                    return {'error': 'Invalid response format: missing vocabulary or structure'}
                
                # Validate vocabulary format
                if not isinstance(suggestion_data['vocabulary'], list):
                    return {'error': 'Invalid response format: vocabulary must be an array'}
                
                # Validate each vocabulary item
                for item in suggestion_data['vocabulary']:
                    if not isinstance(item, dict) or 'word' not in item or 'meaning' not in item:
                        return {'error': 'Invalid response format: vocabulary items must have word and meaning'}
                
                return {
                    'vocabulary': suggestion_data['vocabulary'],
                    'structure': suggestion_data['structure'],
                    'error': None
                }
            except json.JSONDecodeError as e:
                # Nếu không parse được JSON, trả về error
                return {'error': f'Failed to parse JSON response: {str(e)}. Raw content: {content[:200]}'}
        else:
            return {'error': 'No suggestion generated'}
            
    except requests.exceptions.Timeout:
        return {'error': 'Request timeout'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Connection error: Check OpenAI API.'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Request error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def get_topics(category: Optional[str] = None) -> Dict:
    """
    Lấy danh sách topics theo category.
    
    Args:
        category: Category name (general, ielts, work) hoặc None để lấy tất cả
    
    Returns:
        Dict với danh sách topics theo category
    """
    if category:
        category = category.lower()
        if category in TOPIC_CATEGORIES:
            return {
                'status': 'success',
                'category': category,
                'data': TOPIC_CATEGORIES[category]
            }
        else:
            return {
                'status': 'error',
                'message': f'Invalid category: {category}. Available: {", ".join(TOPIC_CATEGORIES.keys())}',
                'data': None
            }
    else:
        # Trả về tất cả categories
        return {
            'status': 'success',
            'data': TOPIC_CATEGORIES
        }


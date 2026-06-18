"""
岗位匹配引擎
"""

from utils.resume_analyzer import analyzer

class JobMatcher:
    """岗位匹配器"""
    
    def __init__(self):
        self.analyzer = analyzer
    
    def match(self, resume_content, job_title, job_requirements=''):
        """
        匹配岗位
        
        Args:
            resume_content: 简历内容
            job_title: 岗位名称
            job_requirements: 岗位要求
            
        Returns:
            dict: 匹配结果
        """
        # 分析简历
        resume_analysis = self.analyzer.analyze(resume_content)
        
        # 提取岗位要求中的关键词
        required_skills = self._extract_required_skills(job_title + ' ' + job_requirements)
        
        # 计算匹配度
        matched_skills = []
        missing_skills = []
        
        for skill in required_skills:
            if skill.lower() in [s.lower() for s in resume_analysis['skills']]:
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        # 计算匹配分数
        if required_skills:
            match_score = int(len(matched_skills) / len(required_skills) * 100)
        else:
            match_score = 50
        
        # 经验匹配加分
        if resume_analysis['experience_years'] >= 3:
            match_score = min(match_score + 10, 100)
        
        return {
            'match_score': match_score,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'resume_skills': resume_analysis['skills'],
            'experience_years': resume_analysis['experience_years'],
            'suggestions': self._generate_match_suggestions(match_score, missing_skills)
        }
    
    def _extract_required_skills(self, job_text):
        """从岗位描述中提取技能要求"""
        from config import SKILL_KEYWORDS
        
        required = []
        for category, keywords in SKILL_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in job_text.lower():
                    required.append(keyword)
        return list(set(required))
    
    def _generate_match_suggestions(self, score, missing_skills):
        """生成匹配建议"""
        suggestions = []
        
        if score >= 80:
            suggestions.append('匹配度很高，建议投递简历')
        elif score >= 60:
            suggestions.append('匹配度一般，可以补充以下技能提升竞争力')
        else:
            suggestions.append('匹配度较低，建议先学习以下技能')
        
        if missing_skills:
            suggestions.append(f'缺失技能：{", ".join(missing_skills)}')
        
        return suggestions

# 全局匹配器实例
matcher = JobMatcher()

"""
简历分析引擎
基于规则引擎的简历分析工具
"""

import re
from config import SKILL_KEYWORDS

class ResumeAnalyzer:
    """简历分析器"""
    
    def __init__(self):
        self.skill_keywords = SKILL_KEYWORDS
    
    def analyze(self, resume_content):
        """
        分析简历内容
        
        Args:
            resume_content: 简历文本内容
            
        Returns:
            dict: 分析结果
        """
        result = {
            'skills': self._extract_skills(resume_content),
            'experience_years': self._extract_experience_years(resume_content),
            'education': self._extract_education(resume_content),
            'projects': self._extract_projects(resume_content),
            'score': 0,
            'suggestions': []
        }
        
        # 计算综合评分
        result['score'] = self._calculate_score(result)
        
        # 生成建议
        result['suggestions'] = self._generate_suggestions(result, resume_content)
        
        return result
    
    def _extract_skills(self, content):
        """提取技能关键词"""
        skills = []
        for category, keywords in self.skill_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    skills.append(keyword)
        return list(set(skills))
    
    def _extract_experience_years(self, content):
        """提取工作年限"""
        patterns = [
            r'(\d+)\s*年\s*经验',
            r'(\d+)\s*年\s*工作',
            r'(\d+)\s*年\s*开发',
            r'(\d+)\s*years?\s*experience'
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0
    
    def _extract_education(self, content):
        """提取学历信息"""
        education_levels = ['博士', '硕士', '研究生', '本科', '大专', '专科']
        for level in education_levels:
            if level in content:
                return level
        return '未知'
    
    def _extract_projects(self, content):
        """提取项目经历数量"""
        project_keywords = ['项目', 'project']
        count = 0
        for keyword in project_keywords:
            count += content.lower().count(keyword.lower())
        return min(count, 10)  # 最多算10个
    
    def _calculate_score(self, result):
        """计算综合评分"""
        score = 0
        
        # 技能分 (最多40分)
        score += min(len(result['skills']) * 5, 40)
        
        # 经验分 (最多30分)
        score += min(result['experience_years'] * 3, 30)
        
        # 学历分 (最多15分)
        education_scores = {'博士': 15, '硕士': 12, '研究生': 12, '本科': 10, '大专': 8, '专科': 8}
        score += education_scores.get(result['education'], 5)
        
        # 项目分 (最多15分)
        score += min(result['projects'] * 3, 15)
        
        return score
    
    def _generate_suggestions(self, result, content):
        """生成优化建议"""
        suggestions = []
        
        if len(result['skills']) < 3:
            suggestions.append('技能描述较少，建议补充更多技术栈关键词')
        
        if result['experience_years'] == 0:
            suggestions.append('未明确标注工作年限，建议添加')
        
        if result['projects'] == 0:
            suggestions.append('缺少项目经历描述，建议补充')
        
        if len(content) < 200:
            suggestions.append('简历内容较短，建议丰富详细描述')
        
        if not suggestions:
            suggestions.append('简历整体不错，可以考虑优化排版和关键词')
        
        return suggestions

# 全局分析器实例
analyzer = ResumeAnalyzer()

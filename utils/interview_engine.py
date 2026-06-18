"""
职途AI - AI面试引擎（本地规则引擎）
智能体Agent：多轮对话、追问机制、个性化评估
"""

import random
import re
from config import INTERVIEW_QUESTIONS, SKILL_KEYWORDS

class InterviewEngine:
    def __init__(self):
        self.questions = INTERVIEW_QUESTIONS
        self.current_questions = []
        self.current_index = 0
        self.conversation = []
        self.job_title = ""
        self.resume_content = ""
        self.ai_personality = "专业面试官"
        self.candidate_answers = []
        self.question_types = []
        self.is_follow_up = False  # 是否处于追问状态
        self.total_questions = 6

    def start(self, job_title, resume_content=''):
        self.current_index = 0
        self.conversation = []
        self.candidate_answers = []
        self.is_follow_up = False

        job_lower = job_title.lower()
        if 'python' in job_lower:
            category, self.ai_personality = 'python', "Python技术专家面试官"
        elif 'java' in job_lower:
            category, self.ai_personality = 'java', "Java架构师面试官"
        elif any(k in job_lower for k in ['前端','front','vue','react']):
            category, self.ai_personality = 'frontend', "前端技术负责人面试官"
        elif any(k in job_lower for k in ['数据','data','分析']):
            category, self.ai_personality = 'data', "数据科学家面试官"
        elif any(k in job_lower for k in ['产品','product']):
            category, self.ai_personality = 'product', "产品总监面试官"
        elif any(k in job_lower for k in ['测试','test']):
            category, self.ai_personality = 'test', "测试专家面试官"
        elif any(k in job_lower for k in ['运维','devops']):
            category, self.ai_personality = 'devops', "DevOps面试官"
        elif any(k in job_lower for k in ['算法','algorithm','ai']):
            category, self.ai_personality = 'algorithm', "算法专家面试官"
        else:
            category, self.ai_personality = 'general', "HR专业面试官"

        base = self.questions.get(category, self.questions['general']).copy()
        if resume_content:
            skills = self._extract_skills(resume_content)
            for s in skills[:3]:
                qs = {
                    'Python': '请介绍Python的GIL机制及其影响',
                    'Java': '请说说Java内存模型和GC机制',
                    'Spring Boot': 'Spring Boot自动配置原理是什么？',
                    'Vue': 'Vue的响应式原理是什么？',
                    'React': 'React虚拟DOM的工作原理？',
                    'Docker': 'Docker和虚拟机有什么区别？',
                    'MySQL': 'MySQL索引优化有什么经验？',
                    'Redis': 'Redis的持久化机制是怎样的？'
                }
                if s in qs:
                    base.append(qs[s])

        num = min(6, max(4, len(base)))
        self.current_questions = random.sample(base, num)[:num]
        self.question_types = ['technical'] * len(self.current_questions)

        # 穿插行为题和场景题
        behavioral = [
            "请描述一个你解决过的技术难题",
            "分享一次团队合作中遇到分歧的经历",
            "描述你在紧迫时间内完成项目的经历"
        ]
        scenario = [
            "线上系统突然故障，你会如何排查？",
            "新技术栈选型，你会如何决策？",
            "产品经理提了不合理的需求，你怎么处理？"
        ]
        if len(self.current_questions) > 1:
            self.current_questions.insert(1, random.choice(behavioral))
            self.question_types.insert(1, 'behavioral')
        if len(self.current_questions) > 3:
            self.current_questions.insert(3, random.choice(scenario))
            self.question_types.insert(3, 'scenario')

        self.total_questions = len(self.current_questions)
        first_q = f"第1题（共{self.total_questions}题）：{self.current_questions[0]}"
        welcome = f"你好！我是{self.ai_personality}，负责{job_title}岗位的模拟面试。\n\n{first_q}"

        self.conversation.append({'role': 'assistant', 'content': welcome})
        return {'message': welcome, 'ai_personality': self.ai_personality, 'total_questions': self.total_questions}

    def reply(self, answer):
        """处理回答 - 修复版：追问后正确进入下一题"""
        self.conversation.append({'role': 'user', 'content': answer})
        self.candidate_answers.append(answer)

        # 如果当前是追问状态，回答追问后跳到下一题
        if self.is_follow_up:
            self.is_follow_up = False
            self.current_index += 1

        if self.current_index >= self.total_questions:
            return {
                'message': '【面试结束】所有问题已回答完毕！请点击"结束面试"查看评估报告。',
                'has_next': False,
                'question_number': self.total_questions,
                'total': self.total_questions
            }

        # 如果回答太短，追问一次（不跳过当前题）
        if len(answer.strip()) < 20:
            follow_up = self._gen_follow_up(self.question_types[self.current_index])
            self.is_follow_up = True
            self.conversation.append({'role': 'assistant', 'content': f"【追问】{follow_up}"})
            return {
                'message': f'【追问】{follow_up}',
                'has_next': True,
                'question_number': self.current_index + 1,
                'total': self.total_questions,
                'is_follow_up': True
            }

        # 正常进入下一题
        self.current_index += 1
        if self.current_index >= self.total_questions:
            return {
                'message': '【面试结束】所有问题已回答完毕！请点击"结束面试"查看评估报告。',
                'has_next': False,
                'question_number': self.total_questions,
                'total': self.total_questions
            }

        next_q = self.current_questions[self.current_index]
        qtype = self.question_types[self.current_index]
        type_label = {'technical': '技术题', 'behavioral': '行为题', 'scenario': '场景题'}.get(qtype, '')

        msg = f"第{self.current_index + 1}题（共{self.total_questions}题）【{type_label}】：{next_q}"
        self.conversation.append({'role': 'assistant', 'content': msg})
        return {
            'message': msg,
            'has_next': True,
            'question_number': self.current_index + 1,
            'total': self.total_questions
        }

    def evaluate(self):
        dims = {'回答完整性': 0, '逻辑清晰度': 0, '技术深度': 0, '表达能力': 0, '问题理解': 0}
        total = 0
        improvements = []

        for i, ans in enumerate(self.candidate_answers):
            score = 0
            ln = len(ans)
            if ln > 200: s, dims['回答完整性'] = 25, dims['回答完整性'] + 25
            elif ln > 100: s, dims['回答完整性'] = 20, dims['回答完整性'] + 20
            elif ln > 50: s, dims['回答完整性'] = 12, dims['回答完整性'] + 12
            else: s, dims['回答完整性'] = 5, dims['回答完整性'] + 5; score += 5

            logic = sum(1 for k in ['首先','其次','然后','最后','第一','第二','总结','因此','所以'] if k in ans)
            if logic >= 3: score += 25; dims['逻辑清晰度'] += 25
            elif logic >= 1: score += 15; dims['逻辑清晰度'] += 15
            else: score += 8; dims['逻辑清晰度'] += 8

            tech = sum(1 for k in ['原理','机制','优化','架构','设计','实现','底层'] if k in ans)
            if tech >= 2: score += 25; dims['技术深度'] += 25
            elif tech >= 1: score += 15; dims['技术深度'] += 15
            else: score += 10; dims['技术深度'] += 10

            if any(k in ans for k in ['例如','比如','实例']):
                score += 15; dims['表达能力'] += 15
            else:
                score += 8; dims['表达能力'] += 8

            score += 10; dims['问题理解'] += 10
            total += min(score, 100)

        n = max(len(self.candidate_answers), 1)
        avg = int(total / n)
        for k in dims: dims[k] = int(dims[k] / n)

        if avg >= 85:
            feedback = '回答非常优秀，逻辑清晰，内容充实，展现了很强的专业素养'
            ai_comment = '【AI评价】表现非常出色！继续保持，在真实面试中注意语速和眼神交流。'
        elif avg >= 70:
            feedback = '回答良好，但可以更加详细和结构化'
            ai_comment = '【AI评价】表现良好，基础扎实。建议使用STAR法则描述项目经历。'
            improvements.append('使用STAR法则组织回答')
        elif avg >= 55:
            feedback = '回答需要改进，建议多练习结构化表达'
            ai_comment = '【AI评价】还有提升空间。每个问题尽量从"是什么-为什么-怎么做"展开。'
            improvements.append('加强技术深度，多了解底层原理')
        else:
            feedback = '回答需要大幅提升，建议系统准备面试'
            ai_comment = '【AI评价】需要大量练习。每题至少回答3-5句话，覆盖核心要点。'
            improvements.append('大幅扩展回答长度，每题至少100字')

        feedback += f'\n\n共回答{n}题，均分{avg}分\n'
        feedback += ' | '.join([f'{k}:{v}分' for k, v in dims.items()])

        if not improvements:
            improvements.append('继续保持，建议多做压力面试练习')

        return {
            'score': avg, 'feedback': feedback, 'ai_comment': ai_comment,
            'improvement_areas': improvements, 'dimensions': dims, 'conversation': self.conversation
        }

    def agent_chat(self, message, user_id=None):
        m = message.lower()
        if any(k in m for k in ['面试','技巧','准备','回答','自我介绍']):
            return {
                'message': '【AI面试教练】准备要点：\n\n技术面：复习基础+刷题+准备项目描述\n行为面：准备5-8个STAR案例\n提问环节：准备2-3个有深度的问题\n\n需要开始模拟面试吗？',
                'suggestions': ['开始模拟面试', '常见面试题', '面试技巧']
            }
        elif any(k in m for k in ['简历','优化','修改','润色']):
            return {
                'message': '【AI简历助手】建议：\n1. 用数据量化成果\n2. STAR法则描述项目\n3. 根据JD调整关键词\n4. 一页原则\n\n上传简历即可AI深度分析！',
                'suggestions': ['上传简历', '岗位匹配', '面试准备']
            }
        return {
            'message': f'我是AI求职助手，可以帮你分析简历、模拟面试、岗位匹配等。你有什么具体问题吗？',
            'suggestions': ['简历分析', '模拟面试', '岗位匹配', '面试技巧']
        }

    def _extract_skills(self, content):
        skills = []
        for cat, kws in SKILL_KEYWORDS.items():
            for kw in kws:
                if kw.lower() in content.lower():
                    skills.append(kw)
        return list(set(skills))

    def _gen_follow_up(self, qtype):
        f = {
            'technical': ['能详细说说实现原理吗？', '实际项目中如何应用的？', '遇到过什么挑战？'],
            'behavioral': ['具体结果如何？', '你在其中扮演什么角色？', '如果重来会怎么做？'],
            'scenario': ['还有其他方案吗？', '如何评估这个方案？', '资源有限时怎么取舍？']
        }
        return random.choice(f.get(qtype, f['technical']))


engine = InterviewEngine()

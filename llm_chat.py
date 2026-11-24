from langchain_openai import ChatOpenAI
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain.messages import SystemMessage,AIMessage,HumanMessage
import json,asyncio
from pydantic import BaseModel

class AnswerSchema(BaseModel):
    answer:str

class ZipSchema(BaseModel):
    zip_sentence:str

def get_llm():
    try:
        load_dotenv(Path(__file__).parent/'.env')
        api_key = os.getenv('OPENAI_API_KEY','')
        base_url = os.getenv('OPENAI_API_BASE','')
        model = os.getenv('AGENT_MODEL','')
        temperature = os.getenv('AGENT_TEMPERATURE','')
        max_tokens = os.getenv('AGENT_MAX_TOKENS','')
        return ChatOpenAI(base_url=base_url,api_key=api_key,model=model,temperature=temperature,max_tokens=max_tokens)
    except Exception as e:
        print(e)
class LLMChat:
    def __init__(self,user_id:str):
        self.user_id = user_id
        if not user_id:
            raise SystemExit('user_id为空')
        self.llm = get_llm()
        self.answer_llm = self.llm
        self.zip_llm = self.llm.with_structured_output(ZipSchema)
        if not self.llm:
            raise SystemExit('LLM 初始化失败')
        self.zip_turns = ''
        self.prompt = """你是一个中小学教学助手，你的任务是根据用户提出的学习问题【{question}】以及之前的对话内容【{zip_turns}】做出相应的回答，与学习无关的内容不要进行回答，回答的内容不要以json的形式进行回复。
        例1：
        提问：1+1等于多少？
        回答：{{"answer":"1+1等于2。"}}
        例2：
        提问：癌症怎么医治？
        回答：{{"answer":"抱歉，我只能回答中小学的学习相关问题，请重新输入您想询问的内容。"}}
        """
        self.zip_prompt = """你是一个将对话进行压缩的助手，你的任务是将用户与AI助手多轮对话内容【{zip_history}】压缩为一句话，压缩的内容一定要以json的形式进行回复并且一定不要曲解其中的任何对话意思。
        例：
        用户：1+1等于多少？
        AI：1+1等于2。
        用户：1*1等于多少？
        AI：1*1等于1。
        压缩后：{{"zip_sentence":"用户询问了1+1等于多少？，1*1等于多少？AI回复了等于2和等于1。"}}
        """
        self.max_turns = 10
        self.history = []
    async def history_zip(self):
        zip_history = self.history
        msg = await self.zip_llm.ainvoke(self.zip_prompt.format(zip_history=zip_history))
        self.zip_turns = msg.zip_sentence
        #return self.zip_turns
    async def chat(self,question:str):
        if len(self.history) >= self.max_turns * 2:
            await self.history_zip()
            self.history = []
        system = SystemMessage(content=self.prompt.format(zip_turns=self.zip_turns or "无",question=question))
        messages = [system] + self.history + [HumanMessage(content=question)]
        
        pieces = []
        async for chunk in self.answer_llm.astream(messages):
            text = chunk.content
            if not text:
                continue
            if isinstance(text,list):
                text = ''.join(str(x) for x in text)
            pieces.append(text)
            yield text
        
        answer = ''.join(pieces)
        self.history.append(HumanMessage(content=question))
        self.history.append(AIMessage(content=answer))

async def main():
    llm_chat = LLMChat('123')
    while True:
        question = input('请输入：(exit退出)')
        if question == 'exit':
            break
        async for piece in llm_chat.chat(question):
            print(piece,end='',flush=True)
        print()
if __name__ == "__main__":
    
    # llm_chat.history.append(HumanMessage(content='1+1等于多少？'))
    # llm_chat.history.append(AIMessage(content='1+1等于2。'))
    # print(asyncio.run(llm_chat.history_zip()))
    asyncio.run(main())






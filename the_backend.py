import fastapi
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
import json
import os
import networkx as nx
from pathlib import Path
from pydantic import BaseModel
BASE_PATH = Path(__file__).parent.resolve()
r = aioredis.Redis(host='127.0.0.1',port=6379,db=1,decode_responses=True,protocol=2,max_connections=200)
app = fastapi.FastAPI()
G = nx.DiGraph()

@app.on_event('startup')
async def init_data():
    if not await r.get('topics_loaded'):
        with open(os.path.join(BASE_PATH,'data/topics.json'),'r',encoding='utf-8') as f:
                topics = json.load(f)
                for topic in topics:
                    await r.rpush(f"{topic['grade']}年级{topic['domain']}考点",topic['description'])
                    topic_dict = {'domin':topic['domain'],'grade_semester':f"{topic['grade']}年级{topic['semester']}期",'description':topic['description'],'chapter':topic['chapter'],'mastery_criteria':';'.join(topic['mastery_criteria'])}
                    topic_text = json.dumps(topic_dict)
                    await r.rpush(f"{topic['id']}",topic_text)
        with open(os.path.join(BASE_PATH,'data/dependencies.json'),'r',encoding='utf-8') as f:
                dependencies = json.load(f)
                for dependency in dependencies:
                    await r.rpush(f"preid_{dependency['topicId']}",dependency['prerequisiteId'])
                    

        with open(os.path.join(BASE_PATH,'data/questions.json'),'r',encoding='utf-8') as f:
            questions = json.load(f)
            for question in questions:
                await r.rpush(f"question_{question['topicId']}",question['prompt'])
        await r.set('topics_loaded',1)
    with open(os.path.join(BASE_PATH,'data/topics.json'),'r',encoding='utf-8') as f:
        topics = json.load(f)
        for topic in topics:
            G.add_node(topic['id'],name=topic['name'])
    with open(os.path.join(BASE_PATH,'data/dependencies.json'),'r',encoding='utf-8') as f:
        dependencies = json.load(f)
        for dependency in dependencies:
            G.add_edge(dependency['prerequisiteId'],dependency['topicId'])

def generate(res_chunks):
    for res_chunk in res_chunks:
        try:
            res_chunk = json.loads(res_chunk)
            yield res_chunk
        except:
            yield res_chunk

# 获取所有考点
@app.get('/api/topics/{domin}/{grade}')
async def get_topics(domin:str,grade:int):
    topics = await r.lrange(f'{grade}年级{domin}考点',0,-1)
    #return StreamingResponse(generate(topics),media_type="application/x-ndjson")
    return topics

# 获取所有考点的详细内容
class TopicQuery(BaseModel):
    id:str
@app.post('/api/topics')
async def get_id(query: TopicQuery):
    p = r.pipeline()
    p.lrange(f'{query.id}',0,1)
    p.lrange(f'question_{query.id}',0,-1)
    res = await p.execute()
    topic = json.loads(res[0][0])
    questions = ';'.join(res[1])
    topic['questions'] = questions
    return {'data':topic}

# 获取所有考点的前导考点
@app.get('/api/topics/{id}/prerequisites')
async def get_prerequisites(id:str):
    prerequisites = await r.lrange(f'preid_{id}',0,-1)
    #return StreamingResponse(generate(prerequisites),media_type="application/x-ndjson")
    return prerequisites

# 获取所有考点的后续考点
@app.get('/api/topics/{id}/descendants')
async def get_descendants(id:str):
    descendants = (await r.lrange(f'preid_{id}',0,-1))[0]
    related_topics = await r.lrange(descendants,0,-1)
    #return StreamingResponse(generate(descendants),media_type="application/x-ndjson")
    return related_topics

# 获取两个考点之间的最短路径
@app.get('/api/path/{start}/{end}')
async def path(start:str,end:str):
    path_nodes = nx.shortest_path(G,start,end)
    paths = []
    for path_node in path_nodes:
        topic = (await r.lrange(f'{path_node}',0,1))[0]
        topic_dict = json.loads(topic)
        paths.append(topic_dict['name'])
    return '\n'.join(paths)

# 获取考点的所有题目
@app.get('/api/questions')
async def get_questions(topicId:str):
    questions = await r.lrange(f'question_{topicId}',0,-1)
    return questions

@app.get('/api/graph')
async def get_graph(start:str,end:str):
    try:
        path_nodes = nx.shortest_path(G,start,end)
    except nx.NetworkXNoPath:
        return {'error':'两个知识点之间不存在学习路径'}
    except nx.NodeNotFound:
        return {'error':'未找到相关知识点'}
    sub = G.subgraph(path_nodes)
    nodes = [{'data':{'id':n,'label':G.nodes[n].get('name',n)}} for n in sub.nodes()]
    edges = [{'data':{'source':u,'target':v}} for u,v in sub.edges()]
    return {'nodes':nodes,'edges':edges}

    


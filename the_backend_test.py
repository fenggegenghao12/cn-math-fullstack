import asyncio,httpx,psutil,time
def find_pid(port=8000):
    for c in psutil.net_connections(kind='inet'):
        if c.laddr and c.laddr.port == port and c.status == 'LISTEN':
            return c.pid
    raise SystemExit(f'端口 {port} 上没有找到监听进程')

PID = find_pid(8000)
proc = psutil.Process(PID)
print(f'目标进程 PID={PID}')

URL = ['http://127.0.0.1:8000/api/topics','http://127.0.0.1:8000/api/graph?start=cnm_p001&end=cnm_p005']
stats = {'ok':0,'fail':0}




async def worker(url, client, stop):
    while not stop.is_set():
        t0 = time.perf_counter()        # ② 开始计时
        try:
            if url == 'http://127.0.0.1:8000/api/topics':
                resp = await client.post(url, json={'id': 'cnm_001'})
            else:
                resp = await client.get(url)
            stats['ok' if resp.status_code == 200 else 'fail'] += 1
        except Exception:
            stats['fail'] += 1
        stats['ms'] += (time.perf_counter() - t0) * 1000   # ③ 结束后累加



async def main():
    for url in URL:
        print(f'压力测试URL={url}')
        for conc in [1,5,10,20,50,100,200]:
            stats.update(ok=0, fail=0, ms=0.0) 
            stop = asyncio.Event()
            limits = httpx.Limits(max_connections=conc,max_keepalive_connections=conc)
            async with httpx.AsyncClient(limits=limits,timeout=10) as c:
                base = proc.memory_info().rss / 1e6
                tasks = [asyncio.create_task(worker(url,c,stop)) for _ in range(conc)]
                peak = base
                for _ in range(60):
                    await asyncio.sleep(1)
                    peak = max(peak,proc.memory_info().rss / 1e6)
                stop.set()
                await asyncio.gather(*tasks,return_exceptions=True)
                # 每档结束时打印
                total = stats['ok'] + stats['fail']
                avg = stats['ms'] / total if total else 0
                print(f'并发{conc:>3} | 成功 {stats["ok"]:>6} | 失败 {stats["fail"]:>4} | 每秒 {stats["ok"]/30:>7.0f} | 平均 {avg:>6.1f}ms | 峰值 {peak:.1f}MB')

if __name__ == '__main__':
    asyncio.run(main())
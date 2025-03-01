import sys
import os

# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)

# 获取当前脚本的父目录的路径，即`qanything_server`目录
current_dir = os.path.dirname(current_script_path)

# 获取`qanything_server`目录的父目录，即`qanything_kernel`
parent_dir = os.path.dirname(current_dir)

# 获取根目录：`qanything_kernel`的父目录
root_dir = os.path.dirname(parent_dir)

# 将项目根目录添加到sys.path
sys.path.append(root_dir)

from handler import *
from qanything_kernel.core.local_doc_qa import LocalDocQA
from sanic import Sanic
from sanic import response as sanic_response

import os
import argparse
from sanic.worker.manager import WorkerManager
from concurrent_log_handler import ConcurrentRotatingFileHandler
import logging
import time

WorkerManager.THRESHOLD = 6000

# 获取当前时间作为日志文件名的一部分
current_time = time.strftime("%Y%m%d_%H%M%S")
# 定义日志文件夹路径
log_folder = './qanything_logs'
# 确保日志文件夹存在
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
# 定义日志文件的完整路径，包括文件夹和文件名
log_file = os.path.join(log_folder, f'log_{current_time}.log')

# 创建一个 logger 实例
logger = logging.getLogger()
# 设置 logger 的日志级别为 INFO，即只记录 INFO 及以上级别的日志信息
logger.setLevel(logging.INFO)

# 创建一个 ConcurrentRotatingFileHandler 实例
# log_file: 日志文件名
# "a": 文件的打开模式，追加模式
# 16*1024*1024: maxBytes，当日志文件达到 512KB 时进行轮转
# 5: backupCount，保留 5 个轮转日志文件的备份
handler = ConcurrentRotatingFileHandler(log_file, "a", 16 * 1024 * 1024, 5)
# 定义日志格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# 设置日志格式
handler.setFormatter(formatter)

# 将 handler 添加到 logger 中，这样 logger 就可以使用这个 handler 来记录日志了
logger.addHandler(handler)

# 接收外部参数mode
parser = argparse.ArgumentParser()
# mode必须是local或online
parser.add_argument('--mode', type=str, default='local', help='local or online')
# 检查是否是local或online，不是则报错
args = parser.parse_args()
if args.mode not in ['local', 'online']:
    raise ValueError('mode must be local or online')

app = Sanic("QAnything")
# 设置请求体最大为 10MB
app.config.REQUEST_MAX_SIZE = 400 * 1024 * 1024

# CORS中间件，用于在每个响应中添加必要的头信息
@app.middleware("response")
async def add_cors_headers(request, response):
    # response.headers["Access-Control-Allow-Origin"] = "http://10.234.10.144:5052"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"  # 如果需要的话

@app.middleware("request")
async def handle_options_request(request):
    if request.method == "OPTIONS":
        headers = {
            # "Access-Control-Allow-Origin": "http://10.234.10.144:5052",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true"  # 如果需要的话
        }
        return sanic_response.text("", headers=headers)


@app.before_server_start
async def init_local_doc_qa(app, loop):
    local_doc_qa = LocalDocQA()
    local_doc_qa.init_cfg(mode=args.mode, logger=logger)
    print(f'init local_doc_qa in {args.mode}', flush=True)
    app.ctx.local_doc_qa = local_doc_qa


app.add_route(document, "/api/docs", methods=['GET'])
app.add_route(new_knowledge_base, "/api/local_doc_qa/new_knowledge_base", methods=['POST'])  # tags=["新建知识库"]
app.add_route(upload_weblink, "/api/local_doc_qa/upload_weblink", methods=['POST'])  # tags=["上传网页链接"]
app.add_route(upload_files, "/api/local_doc_qa/upload_files", methods=['POST'])  # tags=["上传文件"] 
app.add_route(local_doc_chat, "/api/local_doc_qa/local_doc_chat", methods=['POST'])  # tags=["问答接口"] 
app.add_route(list_kbs, "/api/local_doc_qa/list_knowledge_base", methods=['POST'])  # tags=["知识库列表"] 
app.add_route(list_docs, "/api/local_doc_qa/list_files", methods=['POST'])  # tags=["文件列表"]
app.add_route(get_total_status, "/api/local_doc_qa/get_total_status", methods=['POST'])  # tags=["清理数据库"]
app.add_route(clean_files_by_status, "/api/local_doc_qa/clean_files_by_status", methods=['POST'])  # tags=["清理数据库"]
app.add_route(delete_docs, "/api/local_doc_qa/delete_files", methods=['POST'])  # tags=["删除文件"] 
app.add_route(delete_knowledge_base, "/api/local_doc_qa/delete_knowledge_base", methods=['POST'])  # tags=["删除知识库"] 
app.add_route(rename_knowledge_base, "/api/local_doc_qa/rename_knowledge_base", methods=['POST'])  # tags=["重命名知识库"] 

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8777, workers=4)

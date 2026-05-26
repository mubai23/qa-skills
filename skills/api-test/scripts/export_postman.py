#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 api-test Skill 输出的 Markdown 测试用例导出为 Postman Collection JSON 文件。

用法:
  python export_postman.py <markdown_file> [output_dir]

示例:
  python export_postman.py testcases/登录接口测试用例.md
  python export_postman.py testcases/登录接口测试用例.md ./postman

说明:
  - 自动识别 ## 开头的测试维度作为 Postman Folder
  - 自动识别 ### 开头的测试用例作为 Postman Request
  - 提取 curl 格式的请求信息（方法、URL、Headers、Body）
  - 提取预期响应状态码和校验点生成 Postman Tests 脚本
  - 输出 Postman Collection v2.1 格式 JSON
"""

import json
import os
import re
import sys
import uuid


# Postman Collection v2.1 基础模板
COLLECTION_TEMPLATE = {
    "info": {
        "name": "",
        "description": "",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": []
}

FOLDER_TEMPLATE = {
    "name": "",
    "item": []
}

REQUEST_TEMPLATE = {
    "name": "",
    "request": {
        "method": "GET",
        "header": [],
        "body": None,
        "url": {
            "raw": "",
            "host": [""],
            "path": [""],
            "query": [],
            "variable": []
        },
        "description": ""
    },
    "response": [],
    "event": []
}


def generate_pm_tests(expected_status, checks):
    """根据预期状态码和校验点生成 Postman Tests 脚本。"""
    lines = []
    lines.append("// 自动生成的校验脚本")
    lines.append("")

    if expected_status:
        try:
            code = int(expected_status)
            lines.append(f"pm.test('状态码应为 {code}', function() {{")
            lines.append(f"    pm.response.to.have.status({code});")
            lines.append("});")
            lines.append("")
        except ValueError:
            pass

    # 解析校验点
    check_mapping = {
        "code": "jsonData.code",
        "data": "jsonData.data",
        "token": "jsonData.data.token",
        "message": "jsonData.message",
    }

    for check_text in checks:
        check_text = check_text.strip().rstrip("；;")
        if not check_text:
            continue

        # 模式1: "field=value" 或 "field=xxx"
        if "=" in check_text:
            parts = check_text.split("=", 1)
            field = parts[0].strip()
            expected = parts[1].strip()
            pm_field = check_mapping.get(field, f"jsonData.{field}")
            lines.append(f"pm.test('{check_text}', function() {{")
            lines.append(f"    var jsonData = pm.response.json();")
            lines.append(f"    pm.expect({pm_field}).to.eql({expected});")
            lines.append("});")
            lines.append("")

        # 模式2: "xxx 非空"
        elif "非空" in check_text:
            field = check_text.replace("非空", "").strip().rstrip(".")
            pm_field = check_mapping.get(field, f"jsonData.{field}")
            lines.append(f"pm.test('{check_text}', function() {{")
            lines.append(f"    var jsonData = pm.response.json();")
            lines.append(f"    pm.expect({pm_field}).to.not.be.null;")
            lines.append(f"    pm.expect({pm_field}).to.not.be.undefined;")
            lines.append("});")
            lines.append("")

        # 模式3: "xxx 与入参一致"
        elif "与入参一致" in check_text:
            field = check_text.replace("与入参一致", "").strip().rstrip(".")
            pm_field = check_mapping.get(field, f"jsonData.{field}")
            lines.append(f"pm.test('{check_text}', function() {{")
            lines.append(f"    var jsonData = pm.response.json();")
            lines.append(f"    // 注意：需手动将入参变量化（如 pm.variables.get('{field}')）")
            lines.append(f"    pm.expect({pm_field}).to.exist;")
            lines.append("});")
            lines.append("")

        # 模式4: JSONPath 表达式（以 $ 开头）
        elif check_text.startswith("$"):
            lines.append(f"pm.test('{check_text}', function() {{")
            lines.append(f"    var jsonData = pm.response.json();")
            lines.append(f"    pm.expect(jsonData).to.have.nested.property('{check_text.lstrip('$.')}');")
            lines.append("});")
            lines.append("")

    return "\n".join(lines)


def parse_request_block(text):
    """解析请求块，提取 method、url、headers、body。"""
    lines = text.strip().split("\n")
    if not lines:
        return None

    method = "GET"
    url = ""
    headers = []
    body = None
    in_body = False
    body_lines = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if in_body:
                # 空行后可能还有内容或结束
                continue
            continue

        # 第一行：METHOD /path 或 METHOD http://url
        if i == 0:
            parts = line.split(None, 1)
            if len(parts) >= 1:
                method = parts[0].upper()
            if len(parts) >= 2:
                url = parts[1].rstrip("/")
            continue

        # Header 行（在遇到空行和 body 之前）
        if not in_body and ":" in line and not line.startswith("{"):
            key, value = line.split(":", 1)
            headers.append({
                "key": key.strip(),
                "value": value.strip(),
                "type": "text"
            })
            continue

        # Body 开始（JSON）
        if line.startswith("{") or line.startswith("["):
            in_body = True
            body_lines.append(line)
            continue

        if in_body:
            body_lines.append(line)

    # 解析 body
    if body_lines:
        body_str = "\n".join(body_lines)
        try:
            parsed = json.loads(body_str)
            body = {
                "mode": "raw",
                "raw": body_str,
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
        except json.JSONDecodeError:
            body = {
                "mode": "raw",
                "raw": body_str
            }

    return method, url, headers, body


def parse_url(url_str):
    """将 URL 字符串解析为 Postman url 结构。"""
    # 分离 query string
    query_part = ""
    if "?" in url_str:
        url_str, query_part = url_str.split("?", 1)

    # 判断是否完整 URL
    if url_str.startswith("http://") or url_str.startswith("https://"):
        protocol, rest = url_str.split("://", 1)
        host_parts = rest.split("/", 1)
        host_segments = host_parts[0].split(".")
        path_segments = host_parts[1].split("/") if len(host_parts) > 1 else []
    else:
        # 相对路径，用 {{baseUrl}} 占位
        protocol = "http"
        host_segments = ["{{baseUrl}}"]
        path_segments = url_str.lstrip("/").split("/") if url_str.strip("/") else []

    url_obj = {
        "raw": url_str,
        "protocol": protocol,
        "host": host_segments,
        "path": [p for p in path_segments if p],
        "query": [],
        "variable": []
    }

    # 解析 query parameters
    if query_part:
        for param in query_part.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                url_obj["query"].append({"key": key, "value": value})

    return url_obj


def parse_markdown(content):
    """解析 Markdown 内容，按维度分组提取测试用例。"""
    # 先按 ## 分割维度
    dimension_pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
    case_pattern = re.compile(r'^###\s+(.+)$', re.MULTILINE)
    dim_splits = list(dimension_pattern.finditer(content))

    dimensions = []
    for idx, match in enumerate(dim_splits):
        dim_name = match.group(1).strip()
        start = match.end()
        end = dim_splits[idx + 1].start() if idx + 1 < len(dim_splits) else len(content)
        section_text = content[start:end]

        cases = []
        case_matches = list(case_pattern.finditer(section_text))
        for ci, cm in enumerate(case_matches):
            case_title = cm.group(1).strip()
            case_start = cm.end()
            case_end = case_matches[ci + 1].start() if ci + 1 < len(case_matches) else len(section_text)
            case_text = section_text[case_start:case_end]

            # 分离请求块和预期响应块
            # 预期响应以 "预期响应" 开头
            resp_match = re.search(r'预期响应\s*(\d{3})?\s*[:：]?\s*\n?(.*)', case_text, re.DOTALL)
            expected_status = resp_match.group(1) if resp_match and resp_match.group(1) else None

            # 提取请求块（预期响应之前的部分）
            request_text = case_text
            if resp_match:
                request_text = case_text[:resp_match.start()]

            # 提取校验点
            checks = []
            check_match = re.findall(r'校验点\s*[:：]\s*(.+)', case_text)
            if check_match:
                checks_text = check_match[0]
                checks = [c.strip() for c in checks_text.split("，")]

            parsed = parse_request_block(request_text)
            if not parsed:
                continue

            method, url, headers, body = parsed

            cases.append({
                "title": case_title,
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
                "expected_status": expected_status,
                "checks": checks,
                "raw_request": request_text.strip()
            })

        if cases:
            dimensions.append({
                "name": dim_name,
                "cases": cases
            })

    return dimensions


def build_collection(dimensions, collection_name, description=""):
    """根据解析结果构建 Postman Collection。"""
    collection = json.loads(json.dumps(COLLECTION_TEMPLATE))
    collection["info"]["name"] = collection_name
    collection["info"]["description"] = description

    # 尝试提取公共 baseUrl
    base_urls = set()
    for dim in dimensions:
        for case in dim["cases"]:
            if case["url"].startswith("http"):
                base_urls.add(case["url"])

    for dim in dimensions:
        folder = json.loads(json.dumps(FOLDER_TEMPLATE))
        folder["name"] = dim["name"]

        for case in dim["cases"]:
            req = json.loads(json.dumps(REQUEST_TEMPLATE))
            req["name"] = case["title"]
            req["request"]["method"] = case["method"]
            req["request"]["header"] = case["headers"]

            if case["body"]:
                req["request"]["body"] = case["body"]

            req["request"]["url"] = parse_url(case["url"])
            req["request"]["description"] = case["raw_request"]

            # 生成 Tests 脚本
            tests_script = generate_pm_tests(case["expected_status"], case["checks"])
            if tests_script.strip():
                req["event"].append({
                    "listen": "test",
                    "script": {
                        "exec": [tests_script],
                        "type": "text/javascript"
                    }
                })

            folder["item"].append(req)

        collection["item"].append(folder)

    return collection


def export_postman(md_file, output_dir):
    """主导出函数。"""
    if not os.path.exists(md_file):
        print(f"[错误] 文件不存在: {md_file}")
        return None

    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取收集名称（第一个 # 标题）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    collection_name = title_match.group(1).strip() if title_match else os.path.splitext(os.path.basename(md_file))[0]

    # 提取描述（接口信息头之后的文本，到第一个 ## 标题之前）
    desc_match = re.search(r'\[接口信息\](.+?)(?=^##)', content, re.MULTILINE | re.DOTALL)
    description = desc_match.group(0).strip() if desc_match else ""

    dimensions = parse_markdown(content)

    if not dimensions:
        print("[警告] 未找到可解析的测试维度（## 标题）和测试用例（### 标题），请检查文件格式。")
        print("预期格式：")
        print("  ## 正常场景")
        print("  ### API-001 测试标题")
        print("  POST /api/xxx")
        print("  Content-Type: application/json")
        print("  ")
        print("  {\"key\": \"value\"}")
        print("  ")
        print("  预期响应 200:")
        print("  {\"code\": 200}")
        print("  校验点：code=200")
        return None

    collection = build_collection(dimensions, collection_name, description)

    total_cases = sum(len(dim["cases"]) for dim in dimensions)
    base_name = os.path.splitext(os.path.basename(md_file))[0]
    output_path = os.path.join(output_dir, f"{base_name}.postman_collection.json")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已导出 {total_cases} 条用例 → {output_path}")
    print(f"  - {len(dimensions)} 个 Folder（按测试维度）")
    print(f"  - {total_cases} 个 Request")
    print(f"  - 可在 Postman 中通过 Import → File 导入此 JSON 文件")

    return output_path


def main():
    if len(sys.argv) < 2:
        print("用法: python export_postman.py <markdown_file> [output_dir]")
        print("示例: python export_postman.py testcases/登录接口测试用例.md")
        print("      python export_postman.py testcases/登录接口测试用例.md ./postman")
        sys.exit(1)

    md_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(md_file))

    result = export_postman(md_file, output_dir)
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()

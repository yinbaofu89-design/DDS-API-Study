import streamlit as st
import base64
import json
import uuid
import requests
import os
import tempfile
import mimetypes
from datetime import datetime
import time
import pandas as pd

# ページ設定
st.set_page_config(
    page_title="DDS API ラーニングセンター",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== カスタムCSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #dc3545;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #17a2b8;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
        margin: 0.1rem;
    }
    .badge-required {
        background-color: #dc3545;
        color: white;
    }
    .badge-optional {
        background-color: #6c757d;
        color: white;
    }
    .field-table {
        width: 100%;
        border-collapse: collapse;
    }
    .field-table th {
        background-color: #1f77b4;
        color: white;
        padding: 0.5rem;
        text-align: left;
    }
    .field-table td {
        padding: 0.5rem;
        border-bottom: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初期化 ====================
if "history" not in st.session_state:
    st.session_state.history = []
if "txid" not in st.session_state:
    st.session_state.txid = str(uuid.uuid4())
if "filters" not in st.session_state:
    st.session_state.filters = [
        {"id": "c23de41e-f4a7-4b9e-9c1b-5b4eef283ec0", "name": "PCI"},
        {"id": "e58edfb6-bfa2-4256-ae28-ce929ba46bc8", "name": "source code detection"}
    ]
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False
if "learning_history" not in st.session_state:
    st.session_state.learning_history = []
if "current_request" not in st.session_state:
    st.session_state.current_request = None
if "current_response" not in st.session_state:
    st.session_state.current_response = None
if "dds_host" not in st.session_state:
    st.session_state.dds_host = "192.168.2.132"
if "dds_port" not in st.session_state:
    st.session_state.dds_port = "443"
if "use_ssl" not in st.session_state:
    st.session_state.use_ssl = False
if "verify_ssl" not in st.session_state:
    st.session_state.verify_ssl = True

# ==================== MIMEタイプマッピング ====================
def get_mime_type(filename):
    """ファイル名から適切なMIMEタイプを取得"""
    ext = os.path.splitext(filename)[1].lower()
    
    mime_map = {
        '.txt': 'text/plain', '.csv': 'text/csv', '.log': 'text/plain',
        '.ini': 'text/plain', '.cfg': 'text/plain', '.conf': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.dot': 'application/msword', '.dotx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
        '.docm': 'application/vnd.ms-word.document.macroEnabled.12',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
        '.xlsb': 'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.pptm': 'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
        '.pps': 'application/vnd.ms-powerpoint', '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
        '.pdf': 'application/pdf',
        '.eml': 'message/rfc822', '.msg': 'application/vnd.ms-outlook',
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif',
        '.bmp': 'image/bmp', '.tiff': 'image/tiff', '.tif': 'image/tiff',
        '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
        '.zip': 'application/zip', '.7z': 'application/x-7z-compressed',
        '.rar': 'application/vnd.rar', '.tar': 'application/x-tar', '.gz': 'application/gzip',
        '.html': 'text/html', '.htm': 'text/html',
        '.xml': 'text/xml', '.json': 'application/json',
        '.css': 'text/css', '.js': 'application/javascript',
        '.rtf': 'application/rtf',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
    }
    return mime_map.get(ext, 'application/octet-stream')

# ==================== DDS送信関数 ====================
def send_detection_request(file_obj, source_type, dds_url, verify_ssl, data_type="DIM", content_block_id=None, mime_type=None):
    """
    DDSに検出リクエストを送信する共通関数
    """
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        
        if source_type == "file":
            file_mime = get_mime_type(file_obj.name)
            if file_obj.type and file_obj.type != 'application/octet-stream':
                file_mime = file_obj.type
            
            block_id = file_obj.name.replace('.', '-') + "-001"
            
            request_data = {
                "context": [
                    {"name": "common.dataType", "value": ["DIM"]},
                    {"name": "common.application", "value": ["securlet.box"]},
                    {"name": "common.transactionId", "value": [st.session_state.txid]},
                    {"name": "common.filter", "value": [f["id"] for f in st.session_state.filters]},
                    {"name": "common.expectActionsAck", "value": ["true"]}
                ],
                "subject": {
                    "contentBlockId": "subject-001",
                    "mimeType": "text/plain",
                    "data": base64.b64encode(f"ファイル: {file_obj.name}".encode('utf-8')).decode('utf-8')
                },
                "attachments": [
                    {
                        "contentBlockId": block_id,
                        "mimeType": file_mime,
                        "data": b64_data,
                        "name": file_obj.name
                    }
                ]
            }
            
        else:  # message
            block_id = content_block_id or "message-001"
            mime = mime_type or "text/plain"
            
            request_data = {
                "context": [
                    {"name": "common.dataType", "value": [data_type]},
                    {"name": "common.application", "value": ["securlet.box"]},
                    {"name": "common.transactionId", "value": [st.session_state.txid]},
                    {"name": "common.filter", "value": [f["id"] for f in st.session_state.filters]},
                    {"name": "common.expectActionsAck", "value": ["true"]}
                ],
                "subject": {
                    "contentBlockId": block_id,
                    "mimeType": "text/plain",
                    "data": b64_data
                }
            }
        
        json_data = json.dumps(request_data, ensure_ascii=False)
        
        if st.session_state.get("debug_mode", False):
            st.write("**送信するJSON (構造):**")
            debug_data = request_data.copy()
            if "attachments" in debug_data:
                for att in debug_data["attachments"]:
                    att["data"] = f"{att['data'][:100]}... (Base64, {len(att['data'])}文字)"
            if "subject" in debug_data:
                debug_data["subject"]["data"] = f"{debug_data['subject']['data'][:100]}..."
            st.json(debug_data)
        
        response = requests.post(
            dds_url,
            data=json_data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            verify=not verify_ssl,
            timeout=60
        )
        
        try:
            response_json = response.json()
            
            if response.status_code == 201:
                violations = response_json.get("violation", []) or []
                request_id = response_json.get("requestId")
                return violations, request_id, response_json, None
            else:
                error_info = {
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "headers": dict(response.headers)
                }
                return [], None, None, error_info
                
        except Exception as e:
            error_info = {
                "status_code": response.status_code,
                "response_text": response.text,
                "error": str(e)
            }
            return [], None, None, error_info
            
    except requests.exceptions.ConnectionError as e:
        error_info = {
            "error_type": "ConnectionError",
            "message": str(e),
            "dds_url": dds_url
        }
        return [], None, None, error_info
    except Exception as e:
        error_info = {
            "error_type": "Exception",
            "message": str(e)
        }
        import traceback
        error_info["traceback"] = traceback.format_exc()
        return [], None, None, error_info

# ==================== タイトル ====================
st.markdown('<div class="main-header">📚 DDS API ラーニングセンター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Detection REST API 2.0 を正しく使いこなそう！</div>', unsafe_allow_html=True)

# ==================== サイドバー - 設定 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/api-settings.png", width=80)
    st.markdown("## ⚙️ DDSサーバー設定")
    
    dds_host = st.text_input(
        "DDSサーバーIP",
        value=st.session_state.dds_host,
        key="dds_host_input"
    )
    dds_port = st.text_input(
        "ポート",
        value=st.session_state.dds_port,
        key="dds_port_input"
    )
    use_ssl = st.checkbox(
        "SSL/TLSを使用",
        value=st.session_state.use_ssl,
        key="use_ssl_input"
    )
    verify_ssl = st.checkbox(
        "SSL証明書を検証しない",
        value=st.session_state.verify_ssl,
        key="verify_ssl_input",
        help="自己署名証明書を使用する場合にチェック"
    )
    
    # セッション状態を更新
    st.session_state.dds_host = dds_host
    st.session_state.dds_port = dds_port
    st.session_state.use_ssl = use_ssl
    st.session_state.verify_ssl = verify_ssl
    
    protocol = "https" if use_ssl else "http"
    dds_url = f"{protocol}://{dds_host}:{dds_port}/v2.0/DetectionRequests"
    st.caption(f"📡 URL: {dds_url}")
    
    st.divider()
    
    # デバッグモード
    st.session_state.debug_mode = st.checkbox(
        "🐛 デバッグモード",
        value=st.session_state.debug_mode,
        help="送信するJSONの構造を表示します"
    )
    
    st.divider()
    
    # フィルター設定
    st.subheader("📋 検出フィルター")
    st.caption("最大10個までフィルターを追加できます")
    
    filters_to_remove = []
    for i, f in enumerate(st.session_state.filters):
        cols = st.columns([3, 1])
        with cols[0]:
            st.text_input(
                f"フィルター {i+1}",
                value=f["id"],
                key=f"filter_{i}",
                label_visibility="collapsed"
            )
            st.caption(f"📌 {f.get('name', '')}")
        with cols[1]:
            if st.button("🗑️", key=f"remove_{i}", help="このフィルターを削除"):
                filters_to_remove.append(i)
    
    for idx in sorted(filters_to_remove, reverse=True):
        st.session_state.filters.pop(idx)
        st.rerun()
    
    if len(st.session_state.filters) < 10:
        with st.expander("➕ フィルターを追加"):
            new_filter_id = st.text_input(
                "新しいフィルターID (GUID)",
                placeholder="例: 00000000-0000-0000-0000-000000000000",
                key="new_filter_id"
            )
            new_filter_name = st.text_input(
                "フィルター名（任意）",
                placeholder="例: カスタムフィルター",
                key="new_filter_name"
            )
            if st.button("追加", use_container_width=True):
                if new_filter_id:
                    st.session_state.filters.append({
                        "id": new_filter_id,
                        "name": new_filter_name or f"フィルター {len(st.session_state.filters)+1}"
                    })
                    st.rerun()
                else:
                    st.warning("フィルターIDを入力してください")
    
    st.divider()
    
    st.text_input(
        "トランザクションID",
        value=st.session_state.txid,
        key="txid_display",
        disabled=True
    )
    if st.button("🔄 新しいIDを生成", use_container_width=True):
        st.session_state.txid = str(uuid.uuid4())
        st.rerun()

# ==================== タブ ====================
tab1, tab2, tab3 = st.tabs([
    "📁 ファイルアップロード",
    "💬 メッセージ送信",
    "📖 学習センター"
])

# ==================== タブ1: ファイルアップロード ====================
with tab1:
    st.header("📁 ファイルアップロード")
    st.caption("API 2.0仕様: subject(text/plain) + attachments(ファイルデータ)")
    
    supported_types = [
        ".txt", ".csv", ".log", ".ini", ".cfg", ".conf",
        ".doc", ".docx", ".dot", ".dotx", ".docm",
        ".xls", ".xlsx", ".xlsm", ".xlsb",
        ".ppt", ".pptx", ".pptm", ".pps", ".ppsx",
        ".pdf", ".eml", ".msg",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".svg", ".ico",
        ".zip", ".7z", ".rar", ".tar", ".gz",
        ".html", ".htm", ".xml", ".json", ".css", ".js",
        ".rtf", ".odt", ".ods", ".odp"
    ]
    
    uploaded_file = st.file_uploader(
        "検出対象ファイルを選択してください",
        type=supported_types,
        help=f"サポート形式: {len(supported_types)}種類以上のファイル形式"
    )
    
    if uploaded_file:
        file_mime = get_mime_type(uploaded_file.name)
        if uploaded_file.type and uploaded_file.type != 'application/octet-stream':
            file_mime = uploaded_file.type
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ファイル名", uploaded_file.name)
        with col2:
            st.metric("サイズ", f"{uploaded_file.size / 1024:.2f} KB")
        with col3:
            st.metric("MIMEタイプ", file_mime)
        with col4:
            st.metric("形式", uploaded_file.name.split('.')[-1].upper() if '.' in uploaded_file.name else "不明")
        
        # テキストファイルのプレビュー
        if file_mime and "text" in file_mime:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode('utf-8', errors='ignore')
                st.text_area("📄 ファイル内容プレビュー", content[:1000], height=150)
                if len(content) > 1000:
                    st.caption(f"... 他 {len(content) - 1000} 文字")
            except:
                pass
            finally:
                uploaded_file.seek(0)
        
        st.divider()
        
        col1, col2 = st.columns([1, 3])
        with col1:
            send_file_button = st.button("🚀 DDSに送信", type="primary", use_container_width=True, key="send_file")
        
        with col2:
            if st.button("📋 リクエストJSONを確認", use_container_width=True, key="preview_file"):
                st.session_state.show_file_json = True
        
        if st.session_state.get("show_file_json", False):
            with st.expander("📋 リクエストJSON", expanded=True):
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    b64_data = base64.b64encode(file_bytes).decode('utf-8')
                    
                    request_data = {
                        "context": [
                            {"name": "common.dataType", "value": ["DIM"]},
                            {"name": "common.application", "value": ["securlet.box"]},
                            {"name": "common.transactionId", "value": [st.session_state.txid]},
                            {"name": "common.filter", "value": [f["id"] for f in st.session_state.filters]},
                            {"name": "common.expectActionsAck", "value": ["true"]}
                        ],
                        "subject": {
                            "contentBlockId": "subject-001",
                            "mimeType": "text/plain",
                            "data": base64.b64encode(f"ファイル: {uploaded_file.name}".encode('utf-8')).decode('utf-8')
                        },
                        "attachments": [
                            {
                                "contentBlockId": uploaded_file.name.replace('.', '-') + "-001",
                                "mimeType": file_mime,
                                "data": b64_data,
                                "name": uploaded_file.name
                            }
                        ]
                    }
                    st.json(request_data)
                    st.caption(f"Base64データ長: {len(b64_data):,} 文字")
                except Exception as e:
                    st.error(f"JSON生成エラー: {e}")
                finally:
                    uploaded_file.seek(0)
        
        if send_file_button:
            violations, request_id, response_data, error_info = send_detection_request(
                uploaded_file, "file", dds_url, verify_ssl
            )
            
            st.divider()
            st.subheader("📊 レスポンス結果")
            status_color = "green" if response_data and response_data.get("requestId") else "red"
            st.markdown(f"**ステータスコード:** <span style='color:{status_color};font-weight:bold;'>201</span>", unsafe_allow_html=True)
            
            if error_info:
                st.error(f"❌ エラーが発生しました: {error_info}")
            elif violations:
                st.warning(f"⚠️ {len(violations)}件のポリシー違反が検出されました")
                for v in violations:
                    st.info(f"📌 ポリシー: {v.get('name', '不明')} (ID: {v.get('policyId', 'N/A')})")
            else:
                st.success("✅ ポリシー違反はありませんでした")
            
            if response_data:
                with st.expander("📋 レスポンス詳細"):
                    st.json(response_data)
            
            # 履歴に追加
            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": uploaded_file.name,
                "type": "file",
                "mime_type": file_mime,
                "file_size": len(uploaded_file.getvalue()),
                "status": 201 if response_data else "Error",
                "txid": st.session_state.txid
            })

# ==================== タブ2: メッセージ送信 ====================
with tab2:
    st.header("💬 メッセージ送信")
    st.caption("テキストメッセージをsubjectとして送信します")
    
    message_content = st.text_area(
        "📝 検出対象メッセージ",
        placeholder="例: クレジットカード番号: 4111-1111-1111-1111 や 社外秘情報など",
        height=200
    )
    
    with st.expander("⚙️ メッセージ詳細設定"):
        content_block_id = st.text_input(
            "コンテンツブロックID",
            value="message-001"
        )
        data_type = st.selectbox(
            "データタイプ",
            ["DIM", "MSG"],
            index=0,
            help="DIM: ドキュメントタイプ, MSG: メッセージタイプ"
        )
    
    if message_content:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("メッセージ長", f"{len(message_content)} 文字")
        with col2:
            b64_preview = base64.b64encode(message_content.encode('utf-8')).decode('utf-8')
            st.metric("Base64サイズ", f"{len(b64_preview):,} 文字")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            send_message_button = st.button("🚀 DDSに送信", type="primary", use_container_width=True, key="send_message")
        
        with col2:
            if st.button("📋 リクエストJSONを確認", use_container_width=True, key="preview_message"):
                st.session_state.show_message_json = True
        
        if st.session_state.get("show_message_json", False):
            with st.expander("📋 リクエストJSON", expanded=True):
                try:
                    b64_data = base64.b64encode(message_content.encode('utf-8')).decode('utf-8')
                    request_data = {
                        "context": [
                            {"name": "common.dataType", "value": [data_type]},
                            {"name": "common.application", "value": ["securlet.box"]},
                            {"name": "common.transactionId", "value": [st.session_state.txid]},
                            {"name": "common.filter", "value": [f["id"] for f in st.session_state.filters]},
                            {"name": "common.expectActionsAck", "value": ["true"]}
                        ],
                        "subject": {
                            "contentBlockId": content_block_id,
                            "mimeType": "text/plain",
                            "data": b64_data
                        }
                    }
                    st.json(request_data)
                except Exception as e:
                    st.error(f"JSON生成エラー: {e}")
        
        if send_message_button:
            class MessageWrapper:
                def __init__(self, content, name):
                    self.content = content
                    self.name = name
                    self.type = "text/plain"
                    self.size = len(content)
                def read(self):
                    return self.content.encode('utf-8')
                def seek(self, pos):
                    pass
            
            message_wrapper = MessageWrapper(message_content, content_block_id)
            violations, request_id, response_data, error_info = send_detection_request(
                message_wrapper, "message", dds_url, verify_ssl, data_type, content_block_id
            )
            
            st.divider()
            st.subheader("📊 レスポンス結果")
            status_color = "green" if response_data and response_data.get("requestId") else "red"
            st.markdown(f"**ステータスコード:** <span style='color:{status_color};font-weight:bold;'>201</span>", unsafe_allow_html=True)
            
            if error_info:
                st.error(f"❌ エラーが発生しました: {error_info}")
            elif violations:
                st.warning(f"⚠️ {len(violations)}件のポリシー違反が検出されました")
                for v in violations:
                    st.info(f"📌 ポリシー: {v.get('name', '不明')} (ID: {v.get('policyId', 'N/A')})")
            else:
                st.success("✅ ポリシー違反はありませんでした")
            
            if response_data:
                with st.expander("📋 レスポンス詳細"):
                    st.json(response_data)
            
            # 履歴に追加
            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "メッセージ",
                "type": "message",
                "mime_type": "text/plain",
                "file_size": len(message_content),
                "status": 201 if response_data else "Error",
                "txid": st.session_state.txid
            })

# ==================== タブ3: 学習センター ====================
with tab3:
    st.markdown("## 📖 DDS API 学習センター")
    st.markdown("DDS APIの基本を学びましょう。")
    
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "📖 基本ガイド",
        "🎮 練習モード",
        "💻 コード生成",
        "🔧 エラー対処"
    ])
    
    # サブタブ1: 基本ガイド
    with sub_tab1:
        st.markdown("### 🎯 DDS API の基本構造")
        
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown("""
            #### 📋 リクエストの流れ
            
            <div class="step-box">
            <b>Step 1:</b> データを準備（テキストまたはファイル）
            </div>
            <div class="step-box">
            <b>Step 2:</b> データを <span class="highlight">Base64</span> にエンコード
            </div>
            <div class="step-box">
            <b>Step 3:</b> JSON形式でリクエストボディを構築
            </div>
            <div class="step-box">
            <b>Step 4:</b> <span class="highlight">POST</span> メソッドで送信
            </div>
            <div class="step-box">
            <b>Step 5:</b> レスポンスを確認して解析
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            #### 📌 必須フィールド
            
            <table class="field-table">
            <tr><th>フィールド</th><th>説明</th><th>必須</th><th>例</th></tr>
            <tr><td><code>common.application</code></td><td>アプリケーション名</td><td><span class="badge badge-required">必須</span></td><td><code>"securlet.box"</code></td></tr>
            <tr><td><code>common.dataType</code></td><td>データタイプ</td><td><span class="badge badge-required">必須</span></td><td><code>"DIM"</code> または <code>"MSG"</code></td></tr>
            <tr><td><code>common.filter</code></td><td>ポリシーフィルター</td><td><span class="badge badge-required">必須</span></td><td><code>"c23de41e-..."</code></td></tr>
            <tr><td><code>common.transactionId</code></td><td>トランザクションID</td><td><span class="badge badge-required">必須</span></td><td><code>"uuid"</code></td></tr>
            <tr><td><code>subject.data</code></td><td>メッセージ本文</td><td><span class="badge badge-optional">オプション</span></td><td><code>"SGVsbG8g..."</code></td></tr>
            <tr><td><code>attachments[].data</code></td><td>ファイルデータ</td><td><span class="badge badge-optional">オプション</span></td><td><code>"JVBERi0x..."</code></td></tr>
            <tr><td><code>attachments[].mimeType</code></td><td>MIMEタイプ</td><td><span class="badge badge-optional">オプション</span></td><td><code>"application/pdf"</code></td></tr>
            </table>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📦 リクエスト構造")
            st.json({
                "context": [
                    {"name": "common.dataType", "value": ["DIM"]},
                    {"name": "common.application", "value": ["securlet.box"]},
                    {"name": "common.transactionId", "value": ["a32cc030-9776-45ce-ba55-84f9f5afe009"]},
                    {"name": "common.filter", "value": ["c23de41e-f4a7-4b9e-9c1b-5b4eef283ec0"]},
                    {"name": "common.expectActionsAck", "value": ["true"]}
                ],
                "subject": {
                    "contentBlockId": "subject-001",
                    "mimeType": "text/plain",
                    "data": "SGVsbG8gV29ybGQh"
                },
                "attachments": [
                    {
                        "contentBlockId": "file-001",
                        "mimeType": "application/pdf",
                        "data": "JVBERi0xLjQK...",
                        "name": "document.pdf"
                    }
                ]
            })
            
            st.markdown("""
            #### ⚠️ 重要なルール
            
            <div class="info-box">
            ✅ <b>subject</b> は <code>text/plain</code> のみ許可<br>
            ✅ ファイルは <b>attachments</b> に配置<br>
            ✅ データは必ず <b>Base64</b> エンコード<br>
            ✅ <b>contentBlockId</b> は一意であること
            </div>
            """, unsafe_allow_html=True)
    
    # サブタブ2: 練習モード
    with sub_tab2:
        st.markdown("### 🎮 練習モード")
        st.markdown("実際にリクエストを構築してDDSに送信してみましょう。")
        
        # サンプルデータ
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📝 メッセージサンプル")
            sample_messages = {
                "通常テキスト": "今日は良い天気ですね。",
                "機密情報": "クレジットカード番号: 4111-1111-1111-1111",
                "ソースコード": "// ad_users_to_csv.cpp\n#include <iostream>\nusing namespace std;",
                "個人情報": "氏名: 山田太郎\n住所: 東京都渋谷区"
            }
            selected_sample = st.selectbox("サンプルを選択", list(sample_messages.keys()))
            sample_content = sample_messages[selected_sample]
            st.code(sample_content, language="text")
        
        with col2:
            st.markdown("#### 📎 ファイルサンプル")
            st.info("📄 sample.txt: サンプルテキストファイル")
            st.info("📄 sample.csv: CSVデータ")
            st.info("📄 sample.json: JSONデータ")
        
        # Base64エンコード練習
        st.markdown("#### 🔄 Base64エンコード練習")
        practice_text = st.text_input("エンコードするテキストを入力", value=sample_content)
        if practice_text:
            b64_result = base64.b64encode(practice_text.encode('utf-8')).decode('utf-8')
            st.success(f"✅ Base64結果: `{b64_result}`")
            st.caption(f"元のテキスト: {len(practice_text)}文字 → Base64: {len(b64_result)}文字")
    
    # サブタブ3: コード生成
    with sub_tab3:
        st.markdown("### 💻 コード生成")
        st.markdown("各言語のサンプルコードを確認できます。")
        
        language = st.selectbox(
            "言語を選択",
            ["cURL", "Python", "PowerShell"],
            key="code_lang_learning"
        )
        
        sample_request = {
            "context": [
                {"name": "common.dataType", "value": ["DIM"]},
                {"name": "common.application", "value": ["securlet.box"]},
                {"name": "common.transactionId", "value": [str(uuid.uuid4())]},
                {"name": "common.filter", "value": ["c23de41e-f4a7-4b9e-9c1b-5b4eef283ec0"]},
                {"name": "common.expectActionsAck", "value": ["true"]}
            ],
            "subject": {
                "contentBlockId": "message-001",
                "mimeType": "text/plain",
                "data": base64.b64encode("サンプルメッセージ".encode('utf-8')).decode('utf-8')
            }
        }
        
        if language == "cURL":
            code = f'''curl -X POST "{dds_url}" \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json" \\
  -d '{json.dumps(sample_request, ensure_ascii=False)}''
        elif language == "Python":
            code = f'''import requests
import json
import base64

url = "{dds_url}"
headers = {{"Content-Type": "application/json", "Accept": "application/json"}}
data = {json.dumps(sample_request, indent=2, ensure_ascii=False)}

response = requests.post(url, json=data, headers=headers)
print(f"ステータスコード: {{response.status_code}}")
print(f"レスポンス: {{response.json()}}")
'''
                    else:  # PowerShell
            data_json = json.dumps(sample_request, indent=2, ensure_ascii=False)
            code = f'''$headers = @{{
    "Content-Type" = "application/json"
    "Accept" = "application/json"
}}

$body = @'
{data_json}
'@

$response = Invoke-RestMethod -Uri "{dds_url}" -Method Post -Headers $headers -Body $body
$response | ConvertTo-Json -Depth 10
'''
            
        
        
        st.code(code, language=language.lower())
    
    # サブタブ4: エラー対処
    with sub_tab4:
        st.markdown("### 🔧 よくあるエラーと対処法")
        
        errors = [
            {
                "error": "illegal value for common.dataType",
                "cause": "dataTypeに不正な値が設定されている",
                "solution": "「DIM」または「MSG」を指定する",
                "example": '{"name": "common.dataType", "value": ["DIM"]}'
            },
            {
                "error": "incorrect mimeType for subject component",
                "cause": "subjectのMIMEタイプが不正",
                "solution": "subject.mimeTypeは必ず「text/plain」に設定",
                "example": '"mimeType": "text/plain"'
            },
            {
                "error": "Illegal character '.' in base64 content",
                "cause": "Base64エンコードに不正な文字が含まれている",
                "solution": "正しいBase64エンコード方法を使用する",
                "example": 'base64.b64encode(data.encode()).decode("utf-8")'
            },
            {
                "error": "Missing required field: common.application",
                "cause": "必須フィールドが不足している",
                "solution": "contextにcommon.applicationを追加",
                "example": '{"name": "common.application", "value": ["securlet.box"]}'
            },
            {
                "error": "Connection refused / timeout",
                "cause": "DDSサーバーに接続できない",
                "solution": "IPアドレス、ポート、SSL設定を確認",
                "example": f"{dds_url}"
            }
        ]
        
        for err in errors:
            with st.expander(f"❌ {err['error']}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📝 原因:** {err['cause']}")
                    st.markdown(f"**✅ 解決策:** {err['solution']}")
                with col2:
                    st.markdown(f"**💡 正しい例:**")
                    st.code(err['example'], language="json")

# ==================== 送信履歴 ====================
with st.expander("📜 送信履歴", expanded=False):
    if st.session_state.history:
        st.dataframe(
            st.session_state.history,
            column_config={
                "timestamp": "送信日時",
                "source": "送信元",
                "type": "タイプ",
                "mime_type": "MIMEタイプ",
                "file_size": st.column_config.NumberColumn("サイズ(バイト)"),
                "status": "ステータス",
                "txid": "トランザクションID"
            },
            use_container_width=True
        )
        
        if st.button("🗑️ 履歴をクリア", use_container_width=True):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("まだ送信履歴がありません")

# ==================== フッター ====================
st.divider()
st.caption("🔒 Symantec Data Loss Prevention Detection REST API 2.0 - ファイル・メッセージ検出テストツール")
st.caption("📖 参照: [Broadcom DDS API ドキュメント](https://techdocs.broadcom.com/us/en/symantec-security-software/information-security/data-loss-prevention/25-1/about-application-detection/overview-of-the-detection-rest-api-2-0.html)")

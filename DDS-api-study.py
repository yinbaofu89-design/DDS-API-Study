import streamlit as st
import base64
import json
import uuid
import requests
import os
import time
from datetime import datetime
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
    .code-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        overflow-x: auto;
    }
    .highlight {
        background-color: #fff3cd;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        font-weight: bold;
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
    .badge-success {
        background-color: #28a745;
        color: white;
    }
    .badge-warning {
        background-color: #ffc107;
        color: black;
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
    .field-table tr:hover {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初期化 ====================
if "learning_history" not in st.session_state:
    st.session_state.learning_history = []
if "request_counter" not in st.session_state:
    st.session_state.request_counter = 0
if "current_request" not in st.session_state:
    st.session_state.current_request = None
if "current_response" not in st.session_state:
    st.session_state.current_response = None
if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "favorite_examples" not in st.session_state:
    st.session_state.favorite_examples = []

# ==================== ヘルパー関数 ====================
def base64_encode_data(data, is_file=False):
    """データをBase64エンコード"""
    if is_file:
        return base64.b64encode(data).decode('utf-8')
    else:
        return base64.b64encode(data.encode('utf-8')).decode('utf-8')

def generate_transaction_id():
    """一意なトランザクションIDを生成"""
    return str(uuid.uuid4())

def get_filter_presets():
    """フィルタープリセット"""
    return [
        {"id": "c23de41e-f4a7-4b9e-9c1b-5b4eef283ec0", "name": "PCI (クレジットカード)"},
        {"id": "e58edfb6-bfa2-4256-ae28-ce929ba46bc8", "name": "ソースコード検出"},
        {"id": "d4f5a6b7-c8d9-4e5f-8a9b-0c1d2e3f4a5b", "name": "個人情報 (PII)"},
        {"id": "f6e7d8c9-b0a1-4c2d-8e9f-0a1b2c3d4e5f", "name": "機密文書"},
    ]

def get_sample_messages():
    """サンプルメッセージ"""
    return {
        "通常テキスト": "今日は良い天気ですね。",
        "機密情報": "クレジットカード番号: 4111-1111-1111-1111",
        "ソースコード": "// ad_users_to_csv.cpp\n#include <iostream>\nusing namespace std;",
        "個人情報": "氏名: 山田太郎\n住所: 東京都渋谷区\n電話: 090-1234-5678",
        "社外秘": "【社外秘】来期の売上目標は50億円です。"
    }

def get_sample_files():
    """サンプルファイル（バイトデータ）"""
    return {
        "テキストファイル": ("sample.txt", "これはサンプルテキストファイルです。\n機密情報が含まれています。".encode('utf-8')),
        "CSVファイル": ("sample.csv", "name,email,phone\n山田太郎,taro@example.com,090-1234-5678".encode('utf-8')),
        "JSONファイル": ("sample.json", '{"name": "山田太郎", "email": "taro@example.com"}'.encode('utf-8')),
        "社外秘PDF": ("confidential.pdf", b"%PDF-1.4\n%PDF contents would go here\nThis is a sample PDF content."),
        "ソースコード": ("sample.cpp", "// Sample C++ code\n#include <iostream>\nint main() {\n    std::cout << \"Hello\" << std::endl;\n    return 0;\n}".encode('utf-8')),
    }

def generate_curl_code(url, headers, data):
    """cURLコードを生成"""
    header_str = " \\\n  ".join([f'-H "{k}: {v}"' for k, v in headers.items()])
    data_str = json.dumps(data, ensure_ascii=False)
    return f"""curl -X POST "{url}" \\
  {header_str} \\
  -d '{data_str}'"""

def generate_python_code(url, headers, data):
    """Pythonコードを生成"""
    return f'''import requests
import json
import base64

# DDSエンドポイント
url = "{url}"

# ヘッダー
headers = {json.dumps(headers, indent=2)}

# リクエストデータ
data = {json.dumps(data, indent=2)}

# 送信
response = requests.post(url, json=data, headers=headers)

# 結果表示
print(f"ステータスコード: {{response.status_code}}")
print(f"レスポンス: {{response.json()}}")
'''

def generate_powershell_code(url, headers, data):
    """PowerShellコードを生成"""
    header_str = ",\n  ".join([f'@{k} = "{v}"' for k, v in headers.items()])
    data_str = json.dumps(data, ensure_ascii=False)
    return f'''$headers = @{{
  {header_str}
}}

$body = @'
{data_str}
'@

$response = Invoke-RestMethod -Uri "{url}" -Method Post -Headers $headers -Body $body
$response | ConvertTo-Json -Depth 10
'''

# ==================== タイトル ====================
st.markdown('<div class="main-header">📚 DDS API ラーニングセンター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Detection REST API 2.0 を正しく使いこなそう！</div>', unsafe_allow_html=True)

# ==================== サイドバー ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/api-settings.png", width=80)
    st.markdown("## 🎯 学習メニュー")
    
    # 学習進捗
    total_requests = len(st.session_state.learning_history)
    success_count = sum(1 for r in st.session_state.learning_history if r.get("status") == 201)
    st.metric("📊 学習進捗", f"{total_requests} 回", f"✅ {success_count} 回成功")
    
    st.divider()
    
    # クイックナビゲーション
    st.markdown("### 🚀 クイックスタート")
    if st.button("📖 基本ガイド", use_container_width=True):
        st.session_state.active_tab = "基本ガイド"
    if st.button("🎮 練習モード", use_container_width=True):
        st.session_state.active_tab = "練習モード"
    if st.button("💻 コード生成", use_container_width=True):
        st.session_state.active_tab = "コード生成"
    if st.button("🔧 エラー対処", use_container_width=True):
        st.session_state.active_tab = "エラー対処"
    if st.button("📝 クイズ", use_container_width=True):
        st.session_state.active_tab = "クイズ"
    
    st.divider()
    
    # 学習履歴
    st.markdown("### 📜 最近の学習履歴")
    for i, hist in enumerate(st.session_state.learning_history[-5:]):
        status_icon = "✅" if hist.get("status") == 201 else "❌"
        st.caption(f"{status_icon} {hist.get('timestamp', '')[:16]}")
        st.caption(f"  {hist.get('type', '')}: {hist.get('description', '')[:30]}...")
        st.caption("---")

# ==================== タブ ====================
active_tab = st.session_state.get("active_tab", "基本ガイド")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📖 基本ガイド",
    "🎮 練習モード",
    "💻 コード生成",
    "🔧 エラー対処",
    "📝 クイズ"
])

# ==================== タブ1: 基本ガイド ====================
with tab1:
    st.markdown("## 🎯 DDS API の基本構造")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        ### 📋 リクエストの流れ
        
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
        ### 📌 必須フィールド
        
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
        st.markdown("### 📦 リクエスト構造")
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
        ### ⚠️ 重要なルール
        
        <div class="info-box">
        ✅ <b>subject</b> は <code>text/plain</code> のみ許可<br>
        ✅ ファイルは <b>attachments</b> に配置<br>
        ✅ データは必ず <b>Base64</b> エンコード<br>
        ✅ <b>contentBlockId</b> は一意であること<br>
        ✅ ファイルの <b>MIMEタイプ</b> は正確に指定
        </div>
        """, unsafe_allow_html=True)

# ==================== タブ2: 練習モード ====================
with tab2:
    st.markdown("## 🎮 インタラクティブ練習")
    st.markdown("実際にDDSにリクエストを送信して、APIの使い方を学びましょう。")
    
    # ステップ1: 送信タイプの選択
    st.markdown("### Step 1: 送信するデータを選択")
    col1, col2 = st.columns(2)
    with col1:
        send_type = st.radio(
            "データタイプ",
            ["📝 メッセージ", "📎 ファイル"],
            horizontal=True,
            key="practice_send_type"
        )
    
    with col2:
        use_sample = st.checkbox("サンプルデータを使用する", value=True, key="practice_use_sample")
    
    # ステップ2: データ入力
    st.markdown("### Step 2: データを入力")
    
    if send_type == "📝 メッセージ":
        if use_sample:
            sample_messages = get_sample_messages()
            selected_sample = st.selectbox("サンプルメッセージを選択", list(sample_messages.keys()))
            message_content = sample_messages[selected_sample]
            st.text_area("メッセージ内容", value=message_content, height=100, key="practice_message")
        else:
            message_content = st.text_area(
                "メッセージを入力してください",
                placeholder="例: Hello, World!",
                height=100,
                key="practice_message_custom"
            )
        
        # Base64エンコード表示
        if message_content:
            b64_encoded = base64_encode_data(message_content)
            st.markdown(f"""
            <div class="info-box">
            <b>🔄 Base64エンコード結果:</b><br>
            <code>{b64_encoded}</code>
            </div>
            """, unsafe_allow_html=True)
        
        # リクエストプレビュー
        if message_content:
            st.markdown("### Step 3: リクエストを確認")
            request_data = {
                "context": [
                    {"name": "common.dataType", "value": ["MSG"]},
                    {"name": "common.application", "value": ["securlet.box"]},
                    {"name": "common.transactionId", "value": [generate_transaction_id()]},
                    {"name": "common.filter", "value": [get_filter_presets()[0]["id"]]},
                    {"name": "common.expectActionsAck", "value": ["true"]}
                ],
                "subject": {
                    "contentBlockId": "message-001",
                    "mimeType": "text/plain",
                    "data": base64_encode_data(message_content)
                }
            }
            st.json(request_data)
            
            # 送信ボタン
            if st.button("🚀 DDSに送信", type="primary", key="practice_send_btn"):
                send_to_dds(request_data, "メッセージ", message_content[:50])
    
    else:  # ファイル
        if use_sample:
            sample_files = get_sample_files()
            selected_sample = st.selectbox("サンプルファイルを選択", list(sample_files.keys()))
            file_name, file_content = sample_files[selected_sample]
            st.info(f"📎 ファイル名: {file_name} ({len(file_content)} バイト)")
            uploaded_data = file_content
        else:
            uploaded_file = st.file_uploader("ファイルをアップロード", type=["txt", "pdf", "docx", "xlsx", "jpg", "png"])
            if uploaded_file:
                file_name = uploaded_file.name
                uploaded_data = uploaded_file.read()
                st.info(f"📎 {file_name} ({len(uploaded_data)} バイト)")
            else:
                uploaded_data = None
        
        if uploaded_data:
            # Base64エンコード表示
            b64_encoded = base64_encode_data(uploaded_data, is_file=True)
            st.markdown(f"""
            <div class="info-box">
            <b>🔄 Base64エンコード結果:</b><br>
            <code>{b64_encoded[:100]}...</code>
            </div>
            """, unsafe_allow_html=True)
            
            # リクエストプレビュー
            st.markdown("### Step 3: リクエストを確認")
            request_data = {
                "context": [
                    {"name": "common.dataType", "value": ["DIM"]},
                    {"name": "common.application", "value": ["securlet.box"]},
                    {"name": "common.transactionId", "value": [generate_transaction_id()]},
                    {"name": "common.filter", "value": [get_filter_presets()[0]["id"]]},
                    {"name": "common.expectActionsAck", "value": ["true"]}
                ],
                "subject": {
                    "contentBlockId": "subject-001",
                    "mimeType": "text/plain",
                    "data": base64.b64encode(f"ファイル: {file_name}".encode()).decode()
                },
                "attachments": [
                    {
                        "contentBlockId": file_name.replace('.', '-') + "-001",
                        "mimeType": get_mime_type(file_name),
                        "data": b64_encoded,
                        "name": file_name
                    }
                ]
            }
            st.json(request_data)
            
            # 送信ボタン
            if st.button("🚀 DDSに送信", type="primary", key="practice_file_send_btn"):
                send_to_dds(request_data, "ファイル", file_name)

def send_to_dds(request_data, data_type, description):
    """DDSにリクエストを送信する関数"""
    try:
        with st.spinner("⏳ DDSに送信中..."):
            # DDS設定
            dds_host = st.session_state.get("dds_host", "192.168.2.132")
            dds_port = st.session_state.get("dds_port", "443")
            use_ssl = st.session_state.get("use_ssl", False)
            protocol = "https" if use_ssl else "http"
            dds_url = f"{protocol}://{dds_host}:{dds_port}/v2.0/DetectionRequests"
            
            # 送信
            response = requests.post(
                dds_url,
                json=request_data,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=30,
                verify=False
            )
            
            # 結果表示
            st.markdown("### 📊 結果")
            
            if response.status_code == 201:
                st.markdown(f"""
                <div class="success-box">
                ✅ <b>リクエスト成功！</b><br>
                📌 リクエストID: {response.json().get('requestId', 'N/A')}<br>
                📊 ステータスコード: {response.status_code}
                </div>
                """, unsafe_allow_html=True)
                
                # 違反情報
                violations = response.json().get('violation', [])
                if violations:
                    st.warning(f"⚠️ {len(violations)}件のポリシー違反が検出されました")
                    for v in violations:
                        st.info(f"📌 ポリシー: {v.get('name', '不明')} (ID: {v.get('policyId', 'N/A')})")
                else:
                    st.success("✅ ポリシー違反はありませんでした")
                
                # 詳細表示
                with st.expander("📋 レスポンス詳細"):
                    st.json(response.json())
                
                # 学習履歴に追加
                st.session_state.learning_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": data_type,
                    "description": description,
                    "status": response.status_code,
                    "request_id": response.json().get('requestId', 'N/A')
                })
                
                # コード生成用に保存
                st.session_state.current_request = request_data
                st.session_state.current_response = response.json()
                
                # 次のステップへ
                st.info("💡 次のステップ: 「コード生成」タブで実際のコードを確認できます")
                
            else:
                st.markdown(f"""
                <div class="error-box">
                ❌ <b>エラーが発生しました</b><br>
                📊 ステータスコード: {response.status_code}<br>
                📝 エラー詳細: {response.text[:200]}...
                </div>
                """, unsafe_allow_html=True)
                
                # エラー解説
                show_error_guidance(response)
                
                # 学習履歴に追加
                st.session_state.learning_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": data_type,
                    "description": description,
                    "status": response.status_code,
                    "error": response.text[:100]
                })
                
    except requests.exceptions.ConnectionError:
        st.error("❌ DDSサーバーに接続できませんでした。IPアドレスとポートを確認してください。")
    except Exception as e:
        st.error(f"❌ エラーが発生しました: {e}")

def show_error_guidance(response):
    """エラーに対するガイダンスを表示"""
    error_text = response.text.lower()
    
    if "illegal value" in error_text and "datatype" in error_text:
        st.markdown("""
        <div class="info-box">
        <b>💡 エラー解説:</b><br>
        <code>common.dataType</code> に不正な値が設定されています。<br>
        ✅ 正しい値: <code>"DIM"</code> または <code>"MSG"</code>
        </div>
        """, unsafe_allow_html=True)
    elif "incorrect mimetype" in error_text or "mimeType" in error_text:
        st.markdown("""
        <div class="info-box">
        <b>💡 エラー解説:</b><br>
        <code>subject</code> の MIMEタイプが不正です。<br>
        ✅ <code>subject.mimeType</code> は必ず <code>"text/plain"</code> に設定してください。
        </div>
        """, unsafe_allow_html=True)
    elif "base64" in error_text and "illegal character" in error_text:
        st.markdown("""
        <div class="info-box">
        <b>💡 エラー解説:</b><br>
        Base64エンコードに不正な文字が含まれています。<br>
        ✅ 正しいBase64エンコード方法:<br>
        Python: <code>base64.b64encode(data.encode()).decode('utf-8')</code>
        </div>
        """, unsafe_allow_html=True)
    elif "common.application" in error_text:
        st.markdown("""
        <div class="info-box">
        <b>💡 エラー解説:</b><br>
        必須フィールド <code>common.application</code> が不足しています。<br>
        ✅ <code>"context"</code> に <code>{"name": "common.application", "value": ["securlet.box"]}</code> を追加してください。
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
        <b>💡 エラー解説:</b><br>
        不明なエラーが発生しました。「よくあるエラーと対処法」タブで解決策を探してください。
        </div>
        """, unsafe_allow_html=True)

def get_mime_type(filename):
    """ファイル名からMIMEタイプを取得"""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.json': 'application/json',
        '.xml': 'text/xml',
        '.csv': 'text/csv',
        '.cpp': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    }
    return mime_map.get(ext, 'application/octet-stream')

# ==================== タブ3: コード生成 ====================
with tab3:
    st.markdown("## 💻 コード生成")
    st.markdown("実際のリクエストから、各言語のコードを生成します。")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # DDS設定
        st.markdown("### 🔧 DDS接続設定")
        dds_host = st.text_input("DDSサーバーIP", value="192.168.2.132", key="code_host")
        dds_port = st.text_input("ポート", value="443", key="code_port")
        use_ssl = st.checkbox("SSL/TLSを使用", value=False, key="code_ssl")
        protocol = "https" if use_ssl else "http"
        dds_url = f"{protocol}://{dds_host}:{dds_port}/v2.0/DetectionRequests"
        
        # 言語選択
        st.markdown("### 💻 言語選択")
        language = st.selectbox(
            "コードを生成する言語",
            ["cURL", "Python", "PowerShell"],
            key="code_language"
        )
    
    with col2:
        st.markdown("### 📋 クイックアクション")
        if st.button("📥 現在のリクエストを読み込む", use_container_width=True):
            if st.session_state.current_request:
                st.success("✅ リクエストを読み込みました")
            else:
                st.warning("⚠️ まだリクエストがありません。練習モードで送信してください。")
        
        if st.button("📋 クリップボードにコピー", use_container_width=True):
            st.info("💡 コードを選択して Ctrl+C でコピーしてください")
    
    # リクエストデータの表示
    if st.session_state.current_request:
        st.markdown("### 📦 リクエストデータ")
        st.json(st.session_state.current_request)
        
        # コード生成
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = st.session_state.current_request
        
        if language == "cURL":
            code = generate_curl_code(dds_url, headers, data)
        elif language == "Python":
            code = generate_python_code(dds_url, headers, data)
        else:  # PowerShell
            code = generate_powershell_code(dds_url, headers, data)
        
        st.markdown(f"### 💻 {language} コード")
        st.code(code, language=language.lower())
        
        # コード解説
        with st.expander("📖 コード解説", expanded=False):
            if language == "cURL":
                st.markdown("""
                #### cURL コマンドの解説
                - `-X POST`: HTTPメソッドを指定
                - `-H`: ヘッダーを設定
                - `-d`: リクエストボディ（JSON）を指定
                """)
            elif language == "Python":
                st.markdown("""
                #### Python コードの解説
                - `import requests`: HTTPリクエスト用ライブラリ
                - `requests.post()`: POSTリクエストを送信
                - `response.json()`: レスポンスをJSONとして解析
                """)
            else:
                st.markdown("""
                #### PowerShell コードの解説
                - `Invoke-RestMethod`: REST API呼び出しコマンド
                - `-Method Post`: POSTメソッドを指定
                - `-Headers`: ヘッダーを指定
                """)
    else:
        st.info("💡 まず「練習モード」でリクエストを送信してから、ここでコードを生成してください。")

# ==================== タブ4: エラー対処 ====================
with tab4:
    st.markdown("## 🔧 よくあるエラーと対処法")
    
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
            "error": "Failed to decode VALUE_STRING as base64",
            "cause": "データが正しくBase64エンコードされていない",
            "solution": "ファイルのバイナリデータを直接Base64変換",
            "example": 'base64.b64encode(file_data).decode("utf-8")'
        },
        {
            "error": "Missing required field: common.application",
            "cause": "必須フィールドが不足している",
            "solution": "contextにcommon.applicationを追加",
            "example": '{"name": "common.application", "value": ["securlet.box"]}'
        },
        {
            "error": "conflicting-fields: incorrect mimeType",
            "cause": "ファイルのMIMEタイプが一致しない",
            "solution": "ファイルの実際のMIMEタイプを指定",
            "example": '.pdf → "application/pdf"'
        },
        {
            "error": "Connection refused / timeout",
            "cause": "DDSサーバーに接続できない",
            "solution": "IPアドレス、ポート、SSL設定を確認",
            "example": "http://192.168.2.132:443/v2.0/DetectionRequests"
        }
    ]
    
    for i, err in enumerate(errors):
        with st.expander(f"❌ {err['error']}", expanded=i==0):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                **📝 原因:** {err['cause']}
                
                **✅ 解決策:** {err['solution']}
                """)
            with col2:
                st.markdown(f"""
                **💡 正しい例:**
                ```json
                {err['example']}
""")

# ==================== タブ5: クイズ ====================
with tab5:
st.markdown("## 📝 理解度チェック クイズ")
st.markdown("DDS APIの理解を確認しましょう。")

クイズデータ
quiz_data = [
{
"question": "DDS APIでメッセージを送信する場合、subject.mimeTypeは何を指定すべきですか？",
"options": ["text/plain", "text/html", "application/json", "application/octet-stream"],
"correct": 0,
"explanation": "subjectは text/plain のみ許可されます。"
},
{
"question": "ファイルをDDSに送信する場合、データはどのフィールドに配置しますか？",
"options": ["subject", "attachments", "context", "body"],
"correct": 1,
"explanation": "ファイルは attachments フィールドに配置します。"
},
{
"question": "DDS APIで必須のフィールドはどれですか？",
"options": ["common.application", "subject.data", "attachments", "body"],
"correct": 0,
"explanation": "common.application は必須フィールドです。"
},
{
"question": "データをBase64エンコードする理由は何ですか？",
"options": [
"データを圧縮するため",
"バイナリデータをテキスト形式で送信するため",
"暗号化するため",
"サイズを小さくするため"
],
"correct": 1,
"explanation": "Base64はバイナリデータをテキスト形式で表現するためのエンコード方式です。"
},
{
"question": "DDS APIのエンドポイントは何ですか？",
"options": [
"/v1/detection",
"/v2.0/DetectionRequests",
"/api/detect",
"/v2/detection"
],
"correct": 1,
"explanation": "正しいエンドポイントは /v2.0/DetectionRequests です。"
}
]


for i, quiz in enumerate(quiz_data):
st.markdown(f"### 問題 {i+1}: {quiz['question']}")


selected = st.radio(
"回答を選択してください",
quiz["options"],
key=f"quiz_{i}",
index=None
)


if st.button(f"回答を確認 (問題 {i+1})", key=f"check_{i}"):
if selected is None:
st.warning("⚠️ 選択肢を選んでください。")
else:
selected_index = quiz["options"].index(selected)
if selected_index == quiz["correct"]:
st.success("✅ 正解！")
else:
st.error(f"❌ 不正解。正解は: {quiz['options'][quiz['correct']]}")
st.info(f"💡 {quiz['explanation']}")

st.divider()


st.markdown("### 📊 クイズ結果")
if st.button("📈 結果を集計", use_container_width=True):
correct_count = 0
total = len(quiz_data)

for i, quiz in enumerate(quiz_data):


key = f"quiz_{i}"
if key in st.session_state:
selected = st.session_state[key]
if selected and quiz["options"].index(selected) == quiz["correct"]:
correct_count += 1

st.metric("正解率", f"{correct_count}/{total}", f"{correct_count/total*100:.0f}%")

if correct_count == total:
st.balloons()
st.success("🎉 パーフェクト！DDS APIの理解が完璧です！")
elif correct_count >= total * 0.7:
st.success("👍 良好！あと少しで完璧です。")
else:
st.info("📖 もう一度「基本ガイド」を復習してみましょう。")

# ==================== フッター ====================
st.divider()
st.markdown(
"""

<div style="text-align: center; color: #666; font-size: 0.8rem;"> 📚 DDS API ラーニングセンター v1.0<br> Powered by Streamlit | データは保存されません </div> """, unsafe_allow_html=True )
# ==================== DDS設定用の隠し設定 ====================
with st.sidebar:
st.divider()
st.markdown("### 🔧 DDSサーバー設定")
st.session_state.dds_host = st.text_input("ホスト", value="192.168.2.132", key="global_dds_host")
st.session_state.dds_port = st.text_input("ポート", value="443", key="global_dds_port")
st.session_state.use_ssl = st.checkbox("SSL/TLS", value=False, key="global_dds_ssl")

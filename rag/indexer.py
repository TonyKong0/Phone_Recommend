from pathlib import Path
import json
import os

# 配置 HuggingFace 镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

BASE_DIR = Path(__file__).parent.parent
CHROMA_PATH = str(BASE_DIR / "data" / "chroma_db")
PHONES_PATH = str(BASE_DIR / "data" / "phones.json")
COLLECTION_NAME = "phones"


def _build_text(phone: dict) -> str:
    features = "、".join(phone.get("features", []))
    tags = "、".join(phone.get("use_case_tags", []))
    pros = "、".join(phone.get("pros", []))
    cons = "、".join(phone.get("cons", []))
    storage = "/".join(str(s) for s in phone.get("storage_options", []))
    return (
        f"品牌：{phone['brand']}，型号：{phone['model']}，"
        f"发布时间：{phone['release_date']}，价格：{phone['price_cny']}元起。"
        f"处理器：{phone['processor']}，内存：{phone['ram_gb']}GB，"
        f"存储：{storage}GB，屏幕：{phone['display']}。"
        f"电池：{phone['battery_mah']}mAh，充电：{phone['charging_w']}W。"
        f"主摄：{phone['main_camera_mp']}MP，系统：{phone['os']}。"
        f"特色功能：{features}。适用场景：{tags}。"
        f"优点：{pros}。缺点：{cons}。"
        f"简介：{phone['summary']}"
    )


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_index() -> Chroma:
    phones = json.loads(Path(PHONES_PATH).read_text(encoding="utf-8"))
    docs = [
        Document(
            page_content=_build_text(p),
            metadata={
                "id": p["id"],
                "brand": p["brand"],
                "model": p["model"],
                "price_cny": p["price_cny"],
                "is_new": p.get("is_new", False),
            },
        )
        for p in phones
    ]
    embeddings = get_embeddings()
    return Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_PATH,
    )


def load_or_build_index() -> Chroma:
    chroma_path = Path(CHROMA_PATH)
    embeddings = get_embeddings()
    if chroma_path.exists():
        vs = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PATH,
        )
        if vs._collection.count() > 0:
            return vs
    return build_index()

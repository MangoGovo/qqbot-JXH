from pydantic import BaseModel


class WPSExcel(BaseModel):
    """WPS在线文档相关配置"""

    # 分享链接
    share_url: str
    # cookie中的sid参数
    sid: str


class ConfigModel(BaseModel):
    wps_excel: WPSExcel

"""Cliente HTTP educado: intervalo entre requisições, novas tentativas e cache em disco."""

import hashlib
import time
from pathlib import Path

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class Cliente:
    def __init__(self, intervalo=1.5, cache_dir=".cache", cache_horas=20, tentativas=3):
        self.intervalo = intervalo
        self.cache_dir = Path(cache_dir)
        self.cache_horas = cache_horas
        self.tentativas = tentativas
        self._ultimo = 0.0
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})

    def _arquivo_cache(self, url):
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".html")

    def get(self, url):
        arq = self._arquivo_cache(url)
        if arq.exists() and time.time() - arq.stat().st_mtime < self.cache_horas * 3600:
            return arq.read_text(encoding="utf-8")

        erro = None
        for tentativa in range(self.tentativas):
            espera = self.intervalo - (time.time() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.time()
            try:
                r = self.sessao.get(url, timeout=40)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                r.encoding = r.encoding or "utf-8"
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                arq.write_text(r.text, encoding="utf-8")
                return r.text
            except requests.RequestException as e:
                erro = e
                time.sleep(2 ** (tentativa + 1))
        raise RuntimeError(f"Falha ao baixar {url}: {erro}")

from datetime import datetime

from leiloes import enviar
from leiloes.modelo import Leilao


def test_item_para_plataforma():
    l = Leilao(fonte="X", codigo="1", url="https://x/1", uf="PR", modalidade="Extrajudicial (alienação fiduciária)",
               municipio="Pinhão", matricula="1.234", cartorio="Pinhão/PR", area_ha=10.456,
               pracas=[(1, datetime(2026, 10, 14, 16, 0), 1000.0), (2, datetime(2026, 10, 21, 16, 0), 500.0)])
    it = enviar.item(l)
    assert it["chave"] == "PR|1234|pinhao"
    assert it["grupo"] == "Extrajudicial"
    assert it["ultima_praca"] == "2026-10-21T16:00-03:00"
    assert it["pracas"][0] == {"n": 1, "quando": "2026-10-14T16:00-03:00", "valor": 1000.0}
    assert it["area_ha"] == 10.46 and it["devedor"] is None

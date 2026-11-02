"""Primeiro passo da sessão com o robô: só conecta ao Go2 por WebRTC e lê o estado.

Não manda nenhum comando de movimento. Confirma, antes de ligar a ponte:
- que o laptop alcança o robô na rede (IP ou Wi-Fi do robô);
- que a chave AES está certa (firmware >= 1.1.15);
- em que modo de movimento o robô está ("normal", "ai", "mcf"...).

Uso (dentro de mvp-gesto/, com requirements-webrtc.txt instalado):
    export UNITREE_AES_128_KEY=<chave>       # nunca em arquivo do repositório
    python checar_go2.py --ip 192.168.x.y    # robô e laptop no mesmo roteador
    python checar_go2.py --modo ap           # laptop no Wi-Fi do próprio robô
"""
import argparse
import json
import os
import sys

from ponte import RoboGo2WebRTC

API_LER_MODO = 1001  # motion_switcher: só lê o modo atual (1002 troca; aqui nunca)

# o que fazer para cada erro da biblioteca (nomes das classes de unitree_webrtc_connect 2.2.0)
DICAS = {
    "LocalSignalingPortError": "O laptop não alcança o robô: confira o IP, se o robô está ligado e se os dois "
                               "estão na mesma rede (no --modo ap, o laptop no Wi-Fi do próprio robô).",
    "AesKeyRequiredError": "Firmware >= 1.1.15 precisa da chave AES do robô:\n"
                           "  export UNITREE_AES_128_KEY=$(unitree-fetch-aes-key --email <conta> "
                           "--device-type Go2 --sn <número de série> -q)",
    "AesKeyRejectedError": "A chave não é a deste robô. Busque de novo com unitree-fetch-aes-key "
                           "(--device-type Go2), na conta Unitree em que ele foi vinculado.",
    "RobotBusyError": "Outro cliente WebRTC está conectado, em geral o app da Unitree: desconecte-o e tente de novo.",
}


def ler_modo(robo):
    """Pergunta ao robô o modo de movimento atual. Só leitura."""
    from unitree_webrtc_connect import RTC_TOPIC

    robo._conferir_conexao()
    pedido = robo.conn.datachannel.pub_sub.publish_request_new(RTC_TOPIC["MOTION_SWITCHER"], {"api_id": API_LER_MODO})
    resposta = robo._rodar(pedido, robo.PRAZO_S)
    status = resposta["data"]["header"]["status"]["code"]
    if status != 0:
        raise RuntimeError(f"o robô respondeu com código {status}")
    return json.loads(resposta["data"]["data"]).get("name")


def main():
    ap = argparse.ArgumentParser(description="Conecta ao Go2 por WebRTC e lê o estado, sem mover nada")
    ap.add_argument("--ip", help="IP do Go2 (modo sta)")
    ap.add_argument("--modo", choices=["sta", "ap"], default="sta")
    a = ap.parse_args()
    if a.modo == "sta" and not a.ip:
        ap.error("no modo sta, passe --ip")
    chave = os.environ.get("UNITREE_AES_128_KEY")
    print(f"Conectando ({a.modo}{', ' + a.ip if a.ip else ''}; chave AES: {'sim' if chave else 'não'})...")
    try:
        robo = RoboGo2WebRTC(a.ip, chave, a.modo)
    except Exception as e:
        print(f"\nNão conectou: {type(e).__name__}: {e}")
        if type(e).__name__ in DICAS:
            print(DICAS[type(e).__name__])
        sys.exit(1)
    print("Conectado.")
    try:
        modo = ler_modo(robo)
        print(f"Modo de movimento: {modo}")
        if modo != "normal":
            print("Atenção: a ponte espera o modo 'normal'. Troque pelo controle ou pelo app da Unitree.")
    finally:
        robo._rodar(robo.conn.disconnect(), robo.PRAZO_S)
    print("Pronto. Nenhum comando de movimento foi enviado.")


if __name__ == "__main__":
    main()

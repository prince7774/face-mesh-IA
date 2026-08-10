# TecladoIA — Acessibilidade por Expressões Faciais

Controla mouse, teclado e navegação usando gestos faciais captados pela webcam,
via MediaPipe Face Landmarker.

## 1. Instalar dependências

No terminal, dentro da venv `(venv) PS C:\Users\EFG\Downloads\TecladoIA>`:

```powershell
pip install -r requirements.txt
```

## 2. Baixar o modelo do Face Landmarker

O Face Landmarker precisa de um arquivo de modelo `.task` que **não** vem
junto com o pacote pip — precisa ser baixado uma vez:

```powershell
curl -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

Se `curl` não funcionar no PowerShell, baixe direto pelo navegador nesse
link e salve o arquivo `face_landmarker.task` na mesma pasta do projeto
(`TecladoIA/`).

## 3. Rodar

```powershell
python main.py
```

- Uma janela de vídeo abre com overlay de debug (valores de piscar,
  sobrancelha, boca e olhar em tempo real — útil pra calibrar).
- Pressione **q** na janela de vídeo para sair.
- **Levantar as sobrancelhas** alterna entre os modos `mouse` e `navegacao`
  (aparece no console e no overlay).

## Gestos e ações

| Gesto              | Modo mouse                  | Modo navegação                     |
|---------------------|------------------------------|-------------------------------------|
| Piscar duas vezes    | Clique esquerdo              | Enter                                |
| Abrir a boca         | Clique direito                | Voltar página (Alt+Esquerda)         |
| Olhar para a esquerda| Move o cursor para a esquerda | Elemento anterior (Shift+Tab)        |
| Olhar para a direita | Move o cursor para a direita  | Próximo elemento (Tab)               |
| Olhar para cima      | Move o cursor para cima       | Scroll para cima                     |
| Olhar para baixo     | Move o cursor para baixo      | Scroll para baixo                    |
| Levantar sobrancelhas| Alterna modo                  | Alterna modo                         |

## Calibrando

Se algum gesto está disparando fácil demais ou difícil demais, os valores
estão todos centralizados em `config.py`, na seção `THRESHOLDS`. Os números
no overlay de debug (ex. `sobrancelha=0.62`) ajudam a escolher o limiar certo
pro seu rosto e iluminação — normalmente entre 0.3 e 0.6.

## Segurança

O `pyautogui.FAILSAFE` está ativado: se o mouse for movido manualmente para
o canto superior esquerdo da tela, todas as ações automáticas são
interrompidas — é um "botão de pânico" físico caso algo saia do controle.

## Próximos passos possíveis

- Trocar o overlay de debug por uma interface mais amigável (sem termo
  técnico), já que o usuário final pode não precisar ver os números.
- Adicionar um terceiro modo dedicado a atalhos de teclado configuráveis.
- Adicionar feedback sonoro para cada gesto reconhecido, útil para quem não
  quer ficar olhando a tela de debug.

# Controle Remoto LAN

Programa simples para controlar um computador Windows a partir de um laptop Windows na mesma rede Wi-Fi.

Ele foi feito para uso local e autorizado. Por padrao usa a senha facil `controle`, que ja vem preenchida no laptop. Nao exponha este programa na internet.

## Forma mais facil pelo GitHub

No computador principal, abra o PowerShell e rode:

```powershell
irm https://raw.githubusercontent.com/Whesleycampos/controle-remoto-lan/main/baixar_e_instalar_host.ps1 | iex
```

No laptop, abra o PowerShell e rode:

```powershell
irm https://raw.githubusercontent.com/Whesleycampos/controle-remoto-lan/main/baixar_e_instalar_laptop.ps1 | iex
```

Depois disso, o Host fica aberto no computador principal e o laptop tenta encontra-lo automaticamente na rede. Se a busca automatica nao funcionar por causa do firewall/rede, digite no laptop o IP mostrado na janela do Host.

## Como instalar

### No computador que sera controlado

1. Abra a pasta `controle-remoto-lan`.
2. Execute `instalar_host.bat`.
3. Quando terminar, use o atalho `Controle Remoto LAN - Host` na Area de Trabalho.
4. Deixe a janela aberta. Ela mostra o IP que deve ser usado no laptop, por exemplo `http://192.168.1.50:8765`.
5. Se o Windows Firewall perguntar, permita acesso em redes privadas.

A senha padrao e `controle`, e o laptop ja vem com ela preenchida. Para trocar a senha, execute `resetar_senha_host.bat`.

### No laptop

1. Copie a pasta `controle-remoto-lan` para o laptop.
2. Execute `instalar_laptop.bat`.
3. Abra o atalho `Controle Remoto LAN - Laptop`.
4. Aguarde ele encontrar o Host automaticamente. Se nao encontrar, informe o IP mostrado no Host. O campo do IP tambem aceita o endereco completo, como `http://192.168.1.50:8765`.

Depois de conectar, a tela do computador controlado abre em tela cheia no laptop. Para encerrar, clique no botao `Sair` no canto superior direito do laptop.

Se o computador Host tiver dois monitores, o laptop mostra tres botoes no canto superior esquerdo:

- `Duas telas`: mostra as duas telas juntas, lado a lado conforme a organizacao do Windows.
- `Tela 1`: foca apenas no monitor 1.
- `Tela 2`: foca apenas no monitor 2.

O Controle do laptop tenta reconectar automaticamente se o Wi-Fi oscilar, se o streaming cair ou se a sessao precisar ser renovada. Ele mantem a janela aberta e so fecha quando voce encerra pelo laptop.

## Se nao conectar

- Confirme que os dois computadores estao no mesmo Wi-Fi.
- Confirme que o Host esta aberto no computador controlado.
- Use o IP mostrado na janela do Host. O app aceita IP puro ou endereco completo.
- Permita o aplicativo no Windows Firewall para redes privadas.
- Se precisar liberar manualmente, execute `liberar_firewall_host_admin.bat` como Administrador no computador Host.

## Qualidade da imagem

O Host usa qualidade alta por padrao: escala 100%, JPEG 90 e 12 FPS. A imagem fica mais bonita, mas downloads pesados podem aumentar o atraso.

Voce pode trocar o perfil no computador principal:

- `configurar_modo_equilibrado_host.bat`: reduz um pouco o uso de rede.
- `configurar_baixa_latencia_host.bat`: menor atraso, imagem um pouco mais simples.
- `configurar_qualidade_alta_host.bat`: mais nitidez, mas pode atrasar se o Wi-Fi estiver ocupado.

Depois de trocar o perfil, reinicie o Host. Se estiver usando `Duas telas`, a imagem usa muito mais rede; para menor atraso, use `Tela 1` ou `Tela 2`.

## Uso pelo navegador

Tambem e possivel controlar pelo navegador do laptop:

1. Abra o endereco mostrado no Host, por exemplo `http://192.168.1.50:8765`.
2. Digite a senha.
3. Clique em `Tela cheia` se o navegador nao entrar automaticamente.

## Limites conhecidos

- `Ctrl+Alt+Del`, tela bloqueada do Windows e algumas telas de permissao/UAC nao podem ser controladas por seguranca do Windows.
- A qualidade depende da velocidade do Wi-Fi.
- Nao exponha a porta `8765` na internet, roteador, DMZ ou redirecionamento de portas.
- Para parar o acesso pelo laptop, clique em `Sair`.
- Para parar o Host, feche a janela do Host ou pressione `Ctrl+C` nela.

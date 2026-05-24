# Controle Remoto LAN

Programa simples para controlar um computador Windows a partir de um laptop Windows na mesma rede Wi-Fi.

Ele foi feito para uso local e autorizado. Por padrao usa a senha facil `controle`, que ja vem preenchida no laptop. Nao exponha este programa na internet.

Para controlar por outra rede Wi-Fi, use Tailscale nos dois computadores. Assim os dois ficam em uma rede privada virtual e nao precisa abrir porta no roteador.

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

Na instalacao do Host, o modo sempre ligado e ativado automaticamente. Quando o usuario entrar no Windows, o Host sobe em segundo plano, usa a senha `controle` e nao pede confirmacao no computador principal.

## Controlar por outra rede Wi-Fi

Use este modo quando o laptop estiver fora da sua casa/escritorio, em outro Wi-Fi ou no roteador do celular.

1. No computador principal e no laptop, execute `instalar_tailscale_outra_rede.bat`.
2. Abra o Tailscale nos dois computadores e faca login na mesma conta.
3. No computador principal, execute `liberar_firewall_tailscale_admin.bat` como Administrador.
4. No computador principal, deixe o Host aberto.
5. No computador principal, execute `mostrar_ip_tailscale_host.bat` e copie o endereco mostrado, por exemplo `http://100.80.12.34:8765`.
6. No laptop, usando qualquer outra rede Wi-Fi, abra esse endereco no navegador ou digite o IP `100.x.x.x` no app do laptop.

A busca automatica do Host funciona apenas na mesma rede Wi-Fi. Em outra rede, use manualmente o endereco Tailscale `100.x.x.x`.

## Endereco facil

Tambem existe um portal facil de lembrar:

https://conectarwhesley.netlify.app

Na primeira vez, digite ou cole o endereco Tailscale do Host, por exemplo `http://100.80.12.34:8765`. O portal salva esse endereco no navegador do laptop. Depois basta abrir `conectarwhesley.netlify.app` e clicar em `Conectar`.

Nao use redirecionamento de porta, DMZ ou porta aberta no roteador. O modo recomendado para fora da rede local e Tailscale.

## Como instalar

### No computador que sera controlado

1. Abra a pasta `controle-remoto-lan`.
2. Execute `instalar_host.bat`.
3. Quando terminar, use o atalho `Controle Remoto LAN - Host` na Area de Trabalho.
4. O modo sempre ligado ja fica ativado. O Host tambem pode ser aberto manualmente pelo atalho; a janela mostra o IP que deve ser usado no laptop, por exemplo `http://192.168.1.50:8765`.
5. Se o Windows Firewall perguntar, permita acesso em redes privadas.

A senha padrao e `controle`, e o laptop ja vem com ela preenchida. Para trocar a senha, execute `resetar_senha_host.bat`.

Para garantir acesso a qualquer momento enquanto o computador estiver ligado e com o usuario no Windows, execute `ativar_acesso_remoto_sempre.bat`. Ele registra o Host no Agendador do Windows e reinicia o Host automaticamente se o processo cair. Para remover esse modo e fechar o Host, execute `desativar_acesso_remoto_sempre.bat`.

### No laptop

1. Copie a pasta `controle-remoto-lan` para o laptop.
2. Execute `instalar_laptop.bat`.
3. Abra o atalho `Controle Remoto LAN - Laptop`.
4. Aguarde ele encontrar o Host automaticamente. Se nao encontrar, informe o IP mostrado no Host. O campo do IP tambem aceita o endereco completo, como `http://192.168.1.50:8765`.

Depois de conectar, a tela do computador controlado abre em tela cheia no laptop. Para encerrar, clique no botao `Sair` no canto superior direito do laptop.

Mouse e teclado usam um canal rapido TCP na porta `8767`, enquanto imagem/API usam a porta `8765`. Se o Windows Firewall perguntar, permita em redes privadas. Se o mouse ficar travado mas a imagem funcionar, execute `liberar_firewall_host_admin.bat` como Administrador no computador Host.

Se o computador Host tiver dois monitores, o laptop mostra tres botoes no canto superior esquerdo:

- `Duas telas`: mostra as duas telas juntas, lado a lado conforme a organizacao do Windows.
- `Tela 1`: foca apenas no monitor 1.
- `Tela 2`: foca apenas no monitor 2.

O Controle do laptop tenta reconectar automaticamente se o Wi-Fi oscilar, se o streaming cair ou se a sessao precisar ser renovada. Ele mantem a janela aberta e so fecha quando voce encerra pelo laptop.

Se estiver usando pelo navegador, a pagina tambem tenta relogar com a senha `controle` e reabrir o stream quando a rede volta.

## Copiar, colar e arquivos

Enquanto estiver conectado, texto copiado no computador Host e sincronizado automaticamente para o clipboard do laptop. O contrario tambem funciona: texto copiado no laptop vai para o clipboard do Host, facilitando colar dos dois lados.

No canto superior esquerdo do laptop tambem existem botoes de arquivo:

- `Enviar arquivo`: escolhe arquivo(s) do laptop e envia para `Downloads\ControleRemotoLAN` no computador Host.
- `Baixar copiados`: primeiro copie arquivo(s) no computador Host; depois clique nesse botao no laptop para baixar um `.zip` em `Downloads\ControleRemotoLAN`.

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
- O computador principal precisa estar ligado, conectado a internet/rede e com o Windows em uma sessao de usuario que permita capturar a tela.
- Nao exponha a porta `8765` na internet, roteador, DMZ ou redirecionamento de portas.
- Para parar o acesso pelo laptop, clique em `Sair`.
- Para parar o Host, feche a janela do Host ou pressione `Ctrl+C` nela.

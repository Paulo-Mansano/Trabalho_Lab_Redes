# Aplica a rede interna "labredes" + modo promiscuo nas 3 VMs da Fase 1.
# Rode no PowerShell do Windows (host), nao no WSL - VBoxManage e um binario
# do VirtualBox pra Windows. As VMs podem estar desligadas.
#
# Ajuste os nomes abaixo para baterem exatamente com os nomes das VMs
# cadastradas no VirtualBox (Gerenciador de Maquinas Virtuais).

$vms = @("VM-servidor", "VM-cliente", "VM-observador")
$rede = "labredes"

$vboxmanage = "VBoxManage"
if (-not (Get-Command $vboxmanage -ErrorAction SilentlyContinue)) {
    $vboxmanage = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
}

foreach ($vm in $vms) {
    Write-Host "Configurando $vm..."
    & $vboxmanage modifyvm $vm --nic1 intnet --intnet1 $rede --nicpromisc1 allow-all
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Falhou em '$vm' - confira se o nome bate com o do VirtualBox e se a VM esta desligada."
        continue
    }
    Write-Host "  OK: adaptador 1 -> rede interna '$rede', modo promiscuo 'Permitir Tudo'"
}

Write-Host ""
Write-Host "Falta so o IP fixo dentro de cada VM (guest). Dentro de cada uma, no" -ForegroundColor Cyan
Write-Host "PowerShell como Administrador, rode o comando correspondente:" -ForegroundColor Cyan
Write-Host '  VM-servidor:    netsh interface ip set address name="Ethernet" static 10.10.10.10 255.255.255.0'
Write-Host '  VM-cliente:     netsh interface ip set address name="Ethernet" static 10.10.10.20 255.255.255.0'
Write-Host '  VM-observador:  netsh interface ip set address name="Ethernet" static 10.10.10.30 255.255.255.0'
Write-Host ""
Write-Host "Se o nome do adaptador dentro do Windows convidado nao for 'Ethernet'," -ForegroundColor Cyan
Write-Host "confira o nome real com: Get-NetAdapter" -ForegroundColor Cyan

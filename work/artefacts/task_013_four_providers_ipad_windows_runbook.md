---
id: task_013_four_providers_ipad_windows_runbook
type: guide
document_state: current
applicability: reference
version: 1.0
updated: 2026-09-26
depends_on:
  - TASK_013
  - ADR_007
  - ADR_009
---

# `TASK_013`: Hetzner, DigitalOcean, OVHcloud и Selectel — настройка с iPad и Windows

**Версия:** `v1.0`  
**Дата актуализации:** `26.09.2026`  
**Для кого:** для владельца проекта без опыта системного администрирования.  
**Цель:** одна воспроизводимая инструкция для проверки всех четырёх кандидатов `ADR_007` и сбора сопоставимого evidence для `TASK_013`.

> Важно: не нужно держать четыре сервера постоянно. Временную validation VM можно создать, проверить, записать очищенное evidence и удалить сразу после проверки.

---

## 0. Что именно проверяем

Кандидаты `ADR_007`:

1. **Hetzner Cloud**
2. **DigitalOcean**
3. **OVHcloud VPS**
4. **Selectel Cloud**

Текущий `TASK_013` требует практического evidence как минимум для Hetzner, одной альтернативы сценария A (DigitalOcean **или** OVHcloud) и Selectel. Этот runbook покрывает **все четыре**, чтобы при желании получить полную сравнительную таблицу.

Одинаковый целевой результат для каждого реально тестируемого провайдера:

```text
account / control_panel: usable
vm: Ubuntu 24.04 LTS
ssh_from_ipad: passed
ssh_from_windows: passed
ssh_key_authentication_as_deploy: passed
password_authentication: no
permit_root_login: no
docker_service: active_enabled
docker_hello_world: passed
telegram_dns: passed
telegram_https_direct: passed
telegram_getme: passed
server_side_vpn: absent
project_image: passed | not_run_with_reason: ...
health: passed_for_one_shot_contract
restart: not_run_with_reason: persistent_runtime_not_implemented
recreate: not_run_with_reason: persistent_runtime_not_implemented
rollback: not_run_with_reason: previous_good_runtime_image_unavailable
```

Последние четыре строки соответствуют текущему состоянию репозитория на 26.09.2026: `dockerfile` запускает `src.operations.health_check` как одноразовый процесс. Не отмечайте `restart/recreate/rollback` как `passed`, пока в репозитории нет утверждённого persistent runtime.

---

# 1. Карта всей процедуры

```text
1. Подготовить iPad
   ├─ VPN при необходимости
   ├─ Termius
   └─ SSH key iPad

2. Подготовить Windows
   ├─ VPN при необходимости
   ├─ OpenSSH
   ├─ SSH key Windows
   ├─ Git / Python 3.12
   └─ Docker Desktop

3. Узнать текущие VPN exit IPv4
   ├─ iPad: x.x.x.x/32
   └─ Windows: y.y.y.y/32

4. Создать временную VM
   ├─ Ubuntu 24.04
   ├─ >= 2 vCPU
   ├─ >= 4 GB RAM
   ├─ public IPv4
   └─ только SSH TCP/22 с разрешённых /32

5. Войти по SSH с iPad и Windows
6. Создать deploy и добавить оба public key
7. Проверить оба новых входа
8. Отключить root/password SSH
9. Установить Docker
10. Проверить direct outbound к Telegram
11. На Windows собрать image с Git SHA
12. Передать image на VM и запустить
13. Записать redacted evidence
14. Удалить временную VM и проверить платные ресурсы
```

Если шаг не прошёл — не переходите дальше, пока не ясна причина.

---

# 2. Что нельзя публиковать

Никогда не отправляйте в чат, Git, screenshots или логи:

- фактический IPv4 VM;
- домашний/VPN exit IP;
- private SSH key;
- passphrase SSH key;
- Linux password;
- Telegram bot token;
- Telegram user/chat ID;
- API keys;
- платёжные данные;
- `.env`;
- `/etc/personal_ai_platform/app.env`;
- полный `getUpdates`.

В evidence пишите:

```text
firewall_source: owner_vpn_exit_ipv4/32
```

а не реальный IP.

---

# 3. Словарь для новичка

| Термин | Простое значение |
|---|---|
| VM / VPS / Droplet | арендованный виртуальный компьютер |
| Control Panel / Console | сайт провайдера |
| SSH | защищённый вход в командную строку VM |
| SSH key | пара ключей для входа без SSH-пароля |
| Private key | секретная половина; остаётся на устройстве |
| Public key | открытая половина; размещается на сервере |
| Termius | SSH-клиент для iPad |
| OpenSSH | `ssh`, `scp`, `ssh-keygen` в Windows |
| VPN exit IP | адрес, который внешний сайт видит после VPN |
| `/32` | ровно один IPv4 |
| firewall/security group | сетевые правила доступа |
| inbound | соединение в сторону VM |
| outbound | соединение, которое VM начинает наружу |
| deploy | отдельный Linux-администратор проекта |
| sudo | повышение прав для конкретной команды |
| Docker image | упаковка приложения |
| container | запущенный экземпляр image |
| Git SHA | точный идентификатор версии кода |
| evidence | короткое доказательство без секретов |
| long polling | бот сам обращается к Telegram |
| webhook | Telegram приходит на публичный адрес; в V1 не используется |

---

# 4. Что подготовить

## iPad

- Safari;
- VPN-приложение, если нужно;
- Termius;
- Telegram;
- password manager.

## Windows desktop

- актуальный Windows 10/11;
- PowerShell;
- OpenSSH Client;
- Git;
- Python 3.12;
- Docker Desktop;
- VPN, если нужно;
- браузер.

В password manager можно завести запись:

```text
personal_ai_platform / task_013
```

и хранить там Linux password `deploy`, SSH passphrases, Telegram token и прочие секреты. Не сохраняйте их в Markdown проекта.

---

# 5. iPad: создать SSH key

1. Установите Termius из App Store.
2. Включите Face ID/код защиты, если доступно.
3. Откройте `Keychain` / `Keys`.
4. `+` → новый key.
5. Name:

```text
personal_ai_platform_ipad
```

6. Algorithm:

```text
ED25519
```

7. Если задаёте passphrase — уникальную, в password manager.
8. Откройте ключ → **Public Key / Copy Public Key**.

Ожидается одна строка вида:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... personal_ai_platform_ipad
```

**Public Key** можно добавлять провайдеру.  
**Private Key** никому не передаётся.

---

# 6. Windows: OpenSSH и отдельный SSH key

Проверить OpenSSH Client:

```powershell
ssh -V
```

Если команды нет: `Settings → System → Optional features → OpenSSH Client`, установите и откройте PowerShell заново.

Создать ED25519 key:

```powershell
$keyPath = "$HOME\.ssh\personal_ai_platform_windows"
ssh-keygen -t ed25519 -f $keyPath -C "personal_ai_platform_windows"
```

Задайте passphrase и сохраните её в password manager.

Файлы:

```text
C:\Users\<YOU>\.ssh\personal_ai_platform_windows       # PRIVATE
C:\Users\<YOU>\.ssh\personal_ai_platform_windows.pub   # PUBLIC
```

Показать public key:

```powershell
Get-Content "$HOME\.ssh\personal_ai_platform_windows.pub"
```

Скопировать его:

```powershell
Get-Content "$HOME\.ssh\personal_ai_platform_windows.pub" | Set-Clipboard
```

Проверить инструменты:

```powershell
git --version
py -3.12 --version
docker version
```

Для Docker Desktop используйте Linux containers и обычно WSL 2 backend. `docker version` должен показывать Client и Server.

---

# 7. VPN и `/32`

VPN нужен на **вашем устройстве**, если без него панель/SSH недоступны. На VM consumer VPN не ставим.

## iPad

1. Включите нужный VPN.
2. Safari → найдите `what is my ip`.
3. Запишите текущий IPv4 только в защищённую заметку.
4. Добавьте `/32`.

Пример:

```text
203.0.113.10 -> 203.0.113.10/32
```

## Windows

То же самое через браузер при включённом Windows VPN.

Если iPad и Windows используют один VPN exit — адрес может совпасть.

Не создавайте:

```text
TCP 22 from 0.0.0.0/0
```

Создавайте:

```text
TCP 22 from <ipad_vpn_exit_ipv4>/32
TCP 22 from <windows_vpn_exit_ipv4>/32
```

Если VPN IP изменился: сначала добавьте новый `/32`, проверьте новый SSH, затем удалите старый.

---

# 8. Единая конфигурация VM

Для честного сравнения выбирайте ближайшую конфигурацию:

| Параметр | Значение |
|---|---|
| OS | Ubuntu 24.04 LTS x86_64 |
| CPU | >= 2 vCPU |
| RAM | >= 4 GB |
| Public IPv4 | On |
| Extra volume | none |
| Public HTTP/HTTPS | не нужен |
| SSH | TCP/22 только owner `/32` |
| Server-side VPN | absent |
| Backup | Off для краткой validation VM, если платный |
| Region | подходящий доступный, фактическое значение в evidence |

Не зашивайте цену в runbook. Записывайте фактическую цену из панели **в день проверки**.

---

# 9. Hetzner Cloud

## 9.1 Особенности

- первый Ubuntu login: `root`;
- SSH key лучше выбрать при создании VM;
- после создания новый ключ через Console в VM не внедряется автоматически;
- Hetzner Cloud Firewall подходит как основной SSH-фильтр;
- без outbound rules исходящий трафик остаётся разрешённым.

## 9.2 Панель с iPad и Windows

На iPad: включите VPN при необходимости → Safari → Hetzner Cloud Console.  
На Windows: VPN при необходимости → browser → та же Console.

Создайте/откройте Project:

```text
personal_ai_platform
```

## 9.3 Добавить bootstrap Public Key

В Security / SSH Keys добавьте ключ того устройства, с которого будет первый вход:

```text
personal_ai_platform_ipad
```

или:

```text
personal_ai_platform_windows
```

Вставляется только public key.

## 9.4 Создать firewall

`Project → Firewalls → Create Firewall`

Name:

```text
personal_ai_platform_hetzner_ssh_only
```

Inbound:

| Protocol | Port | Source |
|---|---:|---|
| TCP | 22 | `<ipad_vpn_exit_ipv4>/32` |
| TCP | 22 | `<windows_vpn_exit_ipv4>/32` |

Не открывайте 80/443/2375/2376.

## 9.5 Создать VM

`Servers → Add Server`

| Поле | Значение |
|---|---|
| Location | Германия; записать фактический |
| Image | Ubuntu 24.04 |
| Type | ближайший >=2 vCPU / >=4 GB |
| Public IPv4 | On |
| SSH key | bootstrap key |
| Firewall | `personal_ai_platform_hetzner_ssh_only` |
| Volumes | none |
| Backups | Off для временной validation |
| Name | `personal-ai-platform-m02-hetzner` |

До `Create & Buy now` запишите:

```text
server_type
cpu
ram_gb
disk_gb
location
displayed_price
```

## 9.6 iPad SSH

Termius Host:

```text
Label: personal_ai_platform_m02_hetzner_root_initial
Address: <server_ip>
Port: 22
Username: root
Key: bootstrap key
Password: empty
```

## 9.7 Windows SSH

Если Windows key bootstrap:

```powershell
ssh -i "$HOME\.ssh\personal_ai_platform_windows" root@<server_ip>
```

Если bootstrap был iPad, Windows key добавим пользователю `deploy` в общем разделе.

---

# 10. DigitalOcean

## 10.1 Особенности

- VM называется **Droplet**;
- Ubuntu initial login обычно `root`;
- при создании можно выбрать SSH keys;
- Cloud Firewall — отдельный stateful firewall;
- предложенное в UI SSH-правило может быть открыто `All IPv4/All IPv6`: для `TASK_013` его нужно сузить до owner `/32`;
- outbound должен позволять DNS, apt, Docker Hub, Telegram HTTPS и разрешённые API.

## 10.2 Добавить два Public Key

На iPad скопируйте Public Key из Termius.

На Windows:

```powershell
Get-Content "$HOME\.ssh\personal_ai_platform_windows.pub" | Set-Clipboard
```

В DigitalOcean Control Panel найдите `Settings/Security → SSH Keys` и добавьте:

```text
personal_ai_platform_ipad
personal_ai_platform_windows
```

Никакой private key не загружается.

## 10.3 Создать Droplet

На iPad: VPN при необходимости → Safari → DigitalOcean Control Panel.  
На Windows: VPN при необходимости → browser → та же панель.

`Create → Droplets`

Выберите:

| Поле | Значение |
|---|---|
| Region | Frankfurt / ближайший EU, если доступен |
| Image | Ubuntu 24.04 LTS |
| Plan | Basic/shared или аналогичный |
| CPU/RAM | ближайший >=2 vCPU / >=4 GB |
| Authentication | SSH Key |
| SSH keys | iPad + Windows |
| Public IPv4 | On |
| Backups | можно Off для краткой validation |
| Hostname | `personal-ai-platform-m02-digitalocean` |

Запишите фактическую конфигурацию и цену из UI.

## 10.4 Создать Cloud Firewall

`Networking → Firewalls → Create Firewall`

Name:

```text
personal_ai_platform_digitalocean_ssh_only
```

Inbound:

| Type | Protocol | Port | Sources |
|---|---|---:|---|
| SSH | TCP | 22 | `<ipad_vpn_exit_ipv4>/32` |
| SSH | TCP | 22 | `<windows_vpn_exit_ipv4>/32` |

Если UI подставил `All IPv4` или `All IPv6` для SSH — удалите их.

Outbound оставьте достаточным для обычного исходящего доступа.

Примените firewall к:

```text
personal-ai-platform-m02-digitalocean
```

Проверьте ещё раз, что `22 from anywhere` отсутствует.

## 10.5 iPad SSH

Termius:

```text
Label: personal_ai_platform_m02_digitalocean_root_initial
Address: <droplet_ip>
Port: 22
Username: root
Key: personal_ai_platform_ipad
Password: empty
```

## 10.6 Windows SSH

```powershell
ssh -i "$HOME\.ssh\personal_ai_platform_windows" root@<droplet_ip>
```

---

# 11. OVHcloud VPS

## 11.1 Главное отличие

OVHcloud нельзя настраивать точной копией Hetzner.

Для Ubuntu:

- initial user обычно `ubuntu`;
- `root` по умолчанию отключён;
- административные команды выполняются через `sudo`;
- temporary password/initial credentials могут приходить через защищённую ссылку в delivery email;
- при первом password login система может потребовать сменить временный пароль;
- Edge Network Firewall связан прежде всего с anti-DDoS и **не заменяет локальный Linux firewall**.

Поэтому для `TASK_013` основной SSH-фильтр на OVHcloud — **UFW на VM**.

## 11.2 Создать VPS

На iPad: VPN при необходимости → Safari → OVHcloud Control Panel.  
На Windows: то же через browser.

Выберите:

| Поле | Значение |
|---|---|
| OS | Ubuntu 24.04 LTS |
| CPU/RAM | ближайший план >=2 vCore / >=4 GB |
| Region | подходящий европейский; записать фактический |
| Public IPv4 | доступен |
| Extra services | не включать без необходимости |
| Name/label | `personal-ai-platform-m02-ovhcloud` |

До оплаты/заказа запишите показываемую цену и период.

## 11.3 Получить initial credentials

После provisioning откройте delivery email / Control Panel.

Определите:

```text
public IPv4
initial username
```

Для Ubuntu обычно:

```text
ubuntu
```

Но используйте **фактическое имя от OVHcloud**, не угадывайте.

Temporary password сохраняйте только в password manager.

## 11.4 iPad initial SSH

Termius:

```text
Label: personal_ai_platform_m02_ovhcloud_initial
Address: <server_ip>
Port: 22
Username: ubuntu  # или фактический
Password: <если OVH требует initial password>
Key: <если key уже установлен>
```

## 11.5 Windows initial SSH

Если key auth уже настроен:

```powershell
ssh -i "$HOME\.ssh\personal_ai_platform_windows" ubuntu@<server_ip>
```

Если нужен temporary password:

```powershell
ssh ubuntu@<server_ip>
```

После входа немедленно добавьте SSH keys и UFW.

## 11.6 Добавить оба Public Key initial user

На VM:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

iPad key:

```bash
cat >> ~/.ssh/authorized_keys
```

Вставьте одну строку public key → `Enter` → `Ctrl+D`.

Windows key:

```bash
cat >> ~/.ssh/authorized_keys
```

Вставьте `personal_ai_platform_windows.pub` → `Enter` → `Ctrl+D`.

Проверить число непустых строк:

```bash
grep -cve '^[[:space:]]*$' ~/.ssh/authorized_keys
```

## 11.7 Настроить UFW без блокировки себя

Сначала узнайте текущие `/32` обоих устройств.

```bash
sudo apt-get update
sudo apt-get install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

iPad:

```bash
sudo ufw allow from <ipad_vpn_exit_ipv4> to any port 22 proto tcp
```

Windows:

```bash
sudo ufw allow from <windows_vpn_exit_ipv4> to any port 22 proto tcp
```

Проверить правила **до включения**:

```bash
sudo ufw show added
```

Включить:

```bash
sudo ufw enable
sudo ufw status numbered
```

**Не закрывайте текущую SSH-сессию.** Откройте новое подключение и убедитесь, что оно работает.

## 11.8 Edge Network Firewall

Его можно использовать как дополнительный defense-in-depth слой, но основной контроль SSH в этом runbook — UFW.

Evidence:

```text
provider_firewall_model: local_ufw_primary
ovh_edge_network_firewall: optional_defense_in_depth
```

---

# 12. Selectel Cloud

## 12.1 Особенности

- создание: `Продукты → Облачные серверы`;
- в creation flow есть `Безопасность` и `Доступ`;
- Security Groups фильтруют трафик;
- если port security включён и security group не разрешает трафик, он будет запрещён;
- public SSH key можно разместить при создании;
- фактический login смотрите у конкретного сервера в панели, а не угадывайте;
- root password может предлагаться, но постоянный доступ строим на SSH keys.

## 12.2 Создать Security Group

Создайте:

```text
personal_ai_platform_selectel_ssh_only
```

Ingress:

| Protocol | Port | Source |
|---|---:|---|
| TCP | 22 | `<ipad_vpn_exit_ipv4>/32` |
| TCP | 22 | `<windows_vpn_exit_ipv4>/32` |

Не разрешайте `0.0.0.0/0 -> 22`.

Outbound оставьте достаточным для DNS/HTTPS.

## 12.3 Создать VM

На iPad: Safari → Selectel Control Panel → `Продукты → Облачные серверы → Создать сервер`.  
На Windows: те же действия через browser.

### Имя и расположение

```text
personal-ai-platform-m02-selectel
```

Запишите фактический location/pool.

### Источник

```text
Ubuntu 24.04 LTS
```

### Конфигурация

```text
>= 2 vCPU
>= 4 GB RAM
```

### Диски

Стандартный системный диск, без дополнительного volume.

### Интернет

Нужен public internet access и public IPv4.

### Безопасность

Выберите:

```text
personal_ai_platform_selectel_ssh_only
```

### Доступ

Добавьте bootstrap public SSH key iPad или Windows.

Если предлагается password для `root`, сохраняйте его только в password manager, если он вообще нужен.

До `Создать` запишите цену.

## 12.4 Узнать фактический login

После создания:

```text
Продукты → Облачные серверы → <server> → Консоль
```

Посмотрите поле `Логин`.

Используйте именно его.

## 12.5 iPad SSH

```text
Label: personal_ai_platform_m02_selectel_initial
Address: <server_ip>
Port: 22
Username: <login из панели>
Key: bootstrap key
Password: empty, если key auth работает
```

## 12.6 Windows SSH

```powershell
ssh -i "$HOME\.ssh\personal_ai_platform_windows" <username>@<server_ip>
```

Если Windows key не был bootstrap key, добавьте его пользователю `deploy` в следующем общем разделе.

---

# 13. Общий Linux-контур после первого входа

С этого места действия почти одинаковы.

## 13.1 Определить текущего пользователя

```bash
whoami
id
hostname
```

Обычно:

```text
Hetzner:       root
DigitalOcean:  root
OVHcloud:      ubuntu (проверить фактический)
Selectel:      login из панели
```

## 13.2 Обновить Ubuntu

Если root:

```bash
apt-get update
apt-get upgrade -y
timedatectl set-timezone Europe/Berlin
```

Если sudo-user:

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo timedatectl set-timezone Europe/Berlin
```

Проверить:

```bash
hostnamectl
uname -a
df -h
free -h
timedatectl
```

## 13.3 Создать `deploy`

Если root:

```bash
adduser deploy
usermod -aG sudo deploy
```

Если sudo-user:

```bash
sudo adduser deploy
sudo usermod -aG sudo deploy
```

Создайте уникальный Linux password `deploy` и сохраните его в password manager.

## 13.4 Подготовить SSH для deploy

```bash
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudo touch /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Добавить iPad Public Key:

```bash
sudo -u deploy sh -c 'cat >> /home/deploy/.ssh/authorized_keys'
```

Вставьте одну строку → `Enter` → `Ctrl+D`.

Добавить Windows Public Key:

```bash
sudo -u deploy sh -c 'cat >> /home/deploy/.ssh/authorized_keys'
```

Вставьте public key → `Enter` → `Ctrl+D`.

Проверить структуру без вывода полной key material:

```bash
awk 'NF {print NR, $1, substr($2,1,12)"..."}' /home/deploy/.ssh/authorized_keys
```

---

# 14. Критическая проверка: вход `deploy` с обоих устройств

До отключения root/password **не закрывайте первоначальную сессию**.

## 14.1 iPad

Новый Termius Host:

```text
Label: <provider>_personal_ai_platform_deploy
Address: <server_ip>
Port: 22
Username: deploy
Key: personal_ai_platform_ipad
Password: empty
```

После входа:

```bash
whoami
sudo -v
```

Ожидается `deploy`. `sudo -v` попросит Linux password `deploy`.

## 14.2 Windows

```powershell
ssh -i "$HOME\.ssh\personal_ai_platform_windows" deploy@<server_ip>
```

Затем:

```bash
whoami
sudo -v
```

## 14.3 Если один клиент не входит

Не отключайте старый доступ. Проверьте:

- VPN включён;
- VPN exit IP не изменился;
- firewall/security group/UFW разрешает текущий `/32`;
- правильный private key выбран;
- public key в `authorized_keys`;
- права:
  ```bash
  ls -ld /home/deploy/.ssh
  ls -l /home/deploy/.ssh/authorized_keys
  ```
- владелец `deploy deploy`.

---

# 15. Отключить root SSH и password SSH

Только после успешного входа `deploy` с iPad и Windows.

```bash
sudo tee /etc/ssh/sshd_config.d/90_personal_ai_platform.conf >/dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
EOF
```

Проверить синтаксис:

```bash
sudo sshd -t
```

Успех — пустой вывод.

Применить:

```bash
sudo systemctl reload ssh
```

Если service называется `sshd`, сначала проверьте `systemctl status ssh --no-pager`, затем используйте корректное имя.

Откройте ещё одну новую сессию `deploy`.

Итог:

```bash
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication'
```

Evidence:

```text
operator_user: deploy
ssh_key_authentication_as_deploy: passed
permit_root_login: no
password_authentication: no
```

---

# 16. Установить Docker на VM

На VM как `deploy`:

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
```

Проверить:

```bash
sudo systemctl is-active docker
sudo systemctl is-enabled docker
```

Ожидается:

```text
active
enabled
```

Добавить `deploy` в группу Docker:

```bash
sudo usermod -aG docker deploy
```

Теперь **выйдите из SSH и войдите заново**.

Проверка:

```bash
groups
docker --version
docker info
```

В `groups` должна быть группа `docker`.

## 16.1 Hello World

```bash
docker run --rm hello-world
```

Ожидается строка:

```text
Hello from Docker!
```

Код завершения:

```bash
echo $?
```

Ожидается `0`.

Evidence:

```text
docker_service: active_enabled
docker_hello_world: passed
```

## 16.2 Не открывать Docker API

Не создавайте inbound rules `2375`/`2376` и публичный remote Docker API.

---

# 17. Проверить direct outbound к Telegram

VPN на iPad/Windows — только для owner access. VM должна ходить к Telegram напрямую.

## 17.1 DNS

```bash
getent hosts api.telegram.org
```

Успех — имя разрешается. IP из вывода в evidence не нужен.

## 17.2 HTTPS

```bash
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' --max-time 15 https://api.telegram.org
```

Нужен трёхзначный HTTP status. На этом этапе он не обязан быть `200`; важно отсутствие DNS/timeout/TLS error.

## 17.3 Убедиться, что server-side VPN отсутствует

```bash
ip -brief link
ip route
```

Для `TASK_013` специально не создаём `wg0`/`tun0`.

Evidence:

```text
server_side_vpn: absent
telegram_network_profile: direct
telegram_dns: passed
telegram_https_direct: passed
```

---

# 18. Telegram bot: один бот для всех провайдеров

Не создавайте отдельного бота на каждую VM.

## 18.1 На iPad

В официальном Telegram:

1. Найдите официальный `@BotFather`.
2. `/newbot`.
3. Name: `Personal AI Platform`.
4. Username должен заканчиваться на `bot`, например `personal_ai_platform_bot`.
5. Token сохраните **только** в password manager.
6. Удалите token из clipboard после сохранения.
7. Не вставляйте его в Git, Markdown, chat или screenshot.
8. Через `/setjoingroups` отключите добавление в группы, если это соответствует текущей политике проекта.

## 18.2 Windows

Если бот уже создан, второй не нужен. Можно использовать Telegram Desktop, но token всё равно хранится только в password manager.

---

# 19. Проверить Bot API на каждой реально тестируемой VM

На VM как `deploy`.

Ввести token без отображения:

```bash
read -s -p "telegram_bot_token: " telegram_bot_token
echo
```

## 19.1 `getMe`

```bash
curl --fail --silent --show-error "https://api.telegram.org/bot${telegram_bot_token}/getMe"
echo
```

Успех — JSON содержит `"ok":true`. Не сохраняйте полный JSON.

## 19.2 `getWebhookInfo`

```bash
curl --fail --silent --show-error "https://api.telegram.org/bot${telegram_bot_token}/getWebhookInfo"
echo
```

Для V1 ожидается `"url":""`.

## 19.3 Удалить token из shell

```bash
unset telegram_bot_token
```

Проверка:

```bash
if [ -z "${telegram_bot_token+x}" ]; then
  echo "token_variable_removed"
else
  echo "token_variable_still_set"
fi
```

Evidence:

```text
getme: passed
webhook_url: empty
telegram_network_profile: direct
```

---

# 20. Runtime secrets по `ADR_009`

Для реального runtime проект использует:

```text
/etc/personal_ai_platform/app.env
```

Требования:

```text
owner: deploy
mode: 600
```

Создать каталог и пустой защищённый файл:

```bash
sudo install -d -m 700 -o deploy -g deploy /etc/personal_ai_platform
sudo install -m 600 -o deploy -g deploy /dev/null /etc/personal_ai_platform/app.env
```

Проверить только metadata:

```bash
stat -c '%U %G %a %n' /etc/personal_ai_platform/app.env
```

Ожидается:

```text
deploy deploy 600 /etc/personal_ai_platform/app.env
```

Не выводите содержимое этого файла в evidence. Для разовой проверки `TASK_013` bot token безопаснее не сохранять на диск, а использовать временную shell variable.

---

# 21. Windows: получить Git SHA

В PowerShell откройте корень репозитория.

```powershell
git rev-parse --show-toplevel
git status --short
$sha = (git rev-parse --short HEAD).Trim()
$sha
```

Evidence:

```text
commit_sha: <actual_sha>
working_tree: clean | explained
```

Если `git status --short` не пустой, не пишите `clean`.

---

# 22. Windows: канонические проверки проекта

По текущему контракту репозитория:

```powershell
py -3.12 operations/scripts/quality/run_suite.py full
```

Если `pre-commit` установлен согласно проектной инструкции:

```powershell
pre-commit run --all-files
```

Evidence:

```text
canonical_test_suite: passed | not_run_with_reason: <reason>
pre_commit: passed | not_run_with_reason: <reason>
```

---

# 23. Windows: собрать image, привязанный к SHA

```powershell
docker version
$sha = (git rev-parse --short HEAD).Trim()
docker build -f dockerfile --build-arg "APP_VERSION=$sha" -t "personal_ai_platform:$sha" .
docker image ls personal_ai_platform
docker run --rm "personal_ai_platform:$sha"
$LASTEXITCODE
```

Для текущего one-shot health image ожидается exit code `0`.

---

# 24. Передать image на VM с Windows

## 24.1 Сохранить image

```powershell
$sha = (git rev-parse --short HEAD).Trim()
$tar = "personal_ai_platform_$sha.tar"
docker save -o $tar "personal_ai_platform:$sha"
```

## 24.2 `scp`

```powershell
scp -i "$HOME\.ssh\personal_ai_platform_windows" `
  $tar `
  deploy@<server_ip>:/home/deploy/
```

Если timeout — проверьте Windows VPN exit IP и firewall/security group/UFW.

## 24.3 На VM

```bash
docker load -i /home/deploy/personal_ai_platform_<sha>.tar
docker image ls personal_ai_platform
rm /home/deploy/personal_ai_platform_<sha>.tar
```

---

# 25. Запустить project image на VM

```bash
docker run --rm personal_ai_platform:<sha>
container_exit_code=$?
echo "$container_exit_code"
```

Проверить version label:

```bash
docker image inspect personal_ai_platform:<sha> \
  --format '{{ index .Config.Labels "org.opencontainers.image.version" }}'
```

Должен вернуться тот же SHA.

Evidence:

```text
image_tag: personal_ai_platform:<sha>
project_container_exit_code: 0
reported_version_matches_sha: true
```

---

# 26. Health / restart / recreate / rollback: текущая честная граница

Текущий `dockerfile` содержит Docker `HEALTHCHECK`, но основной `CMD` запускает `python -m src.operations.health_check` и завершается.

Это **one-shot validation image**, а не постоянный daemon/service.

Поэтому корректное evidence сейчас:

```text
health: passed_for_one_shot_contract
restart: not_run_with_reason: persistent_runtime_not_implemented
recreate: not_run_with_reason: persistent_runtime_not_implemented
rollback: not_run_with_reason: previous_good_runtime_image_unavailable
```

Не придумывайте `docker restart`, `docker compose` или `systemd` service, которого нет в утверждённом deployment contract.

---

# 27. Evidence каждого провайдера

Используйте отдельный блок для каждой фактически созданной VM.

```text
provider_validation:
  provider: <hetzner|digitalocean|ovhcloud|selectel>
  validation_date: 2026-__-__

  account:
    ipad_access: passed | failed
    windows_access: passed | failed
    local_vpn_required_ipad: true | false
    local_vpn_required_windows: true | false
    registration: passed | preexisting | not_tested
    payment: passed | not_tested

  offer:
    displayed_price: <amount + billing period>
    location: <actual>
    server_type: <actual>
    cpu: <actual>
    ram_gb: <actual>
    disk_gb: <actual>
    image: ubuntu_24_04

  network:
    public_ipv4: present_redacted
    ssh_source: owner_vpn_exit_ipv4_32
    public_http_ports_open: false
    server_side_vpn: absent

  ssh:
    ipad_as_deploy: passed | not_run
    windows_as_deploy: passed | not_run
    permit_root_login: no
    password_authentication: no

  docker:
    service: active_enabled
    hello_world: passed
    image_tag: personal_ai_platform:<sha>
    project_container_exit_code: 0
    reported_version_matches_sha: true

  telegram:
    dns: passed
    https_direct: passed
    getme: passed
    webhook_url: empty
    network_profile: direct

  deployment:
    health: passed_for_one_shot_contract
    restart: not_run_with_reason: persistent_runtime_not_implemented
    recreate: not_run_with_reason: persistent_runtime_not_implemented
    rollback: not_run_with_reason: previous_good_runtime_image_unavailable

  cleanup:
    vm_deleted: true | false
    paid_extra_resources_checked: true | false
```

Provider-specific firewall:

```text
Hetzner:
  primary: hetzner_cloud_firewall
  name: personal_ai_platform_hetzner_ssh_only

DigitalOcean:
  primary: digitalocean_cloud_firewall
  name: personal_ai_platform_digitalocean_ssh_only

OVHcloud:
  primary: local_ufw
  ovh_edge_network_firewall: optional_defense_in_depth

Selectel:
  primary: selectel_security_group
  name: personal_ai_platform_selectel_ssh_only
```

---

# 28. Сравнительная таблица `ADR_007`

| Критерий | Hetzner | DigitalOcean | OVHcloud | Selectel |
|---|---|---|---|---|
| Account доступен без VPN | | | | |
| Account доступен с owner VPN | | | | |
| Регистрация | | | | |
| Оплата | | | | |
| Цена validation VM | | | | |
| Region/location | | | | |
| CPU/RAM/Disk | | | | |
| SSH с iPad | | | | |
| SSH с Windows | | | | |
| SSH ограничен `/32` | | | | |
| Ubuntu 24.04 | | | | |
| Docker | | | | |
| Telegram direct outbound | | | | |
| Git-SHA image | | | | |
| Recovery console | | | | |
| Простота панели 1–5 | | | | |
| VM удалена после теста | | | | |
| Неожиданные ограничения | | | | |

Не выбирайте победителя только по дизайну панели или рекламной цене.

---

# 29. Удалить временную VM после evidence

Это обязательный финансовый cleanup.

До удаления сохраните Git SHA, provider, location, server type, CPU/RAM/Disk, displayed price, SSH/Docker/Telegram results и deployment limitations. Server IP в evidence не нужен.

## 29.1 Hetzner

Удалите validation server и отдельно проверьте, не остались ли платные Volumes, Primary IPs, Snapshots, Backups или Load Balancers.

## 29.2 DigitalOcean

Droplet → `Settings/Actions/More → Destroy`. После удаления проверьте Volumes, Snapshots, Reserved IPs и Backups. Не предполагайте, что удаление Droplet удалило каждый associated resource.

## 29.3 OVHcloud

Действия зависят от текущего типа заказа. Внимательно прочитайте `Terminate / Cancel / Delete / Renewal` и убедитесь, что временный VPS не продолжает продлеваться/биллинговаться. Не удаляйте другие услуги аккаунта.

## 29.4 Selectel

`Продукты → Облачные серверы → <validation server> → Удалить`. Затем проверьте volumes/disks, public/floating IP, snapshots и другие платные ресурсы.

Evidence:

```text
cleanup:
  vm_deleted: true
  paid_extra_resources_checked: true
```

---

# 30. Если VPN exit IP поменялся

Симптом: новый SSH получает `Connection timed out`.

- **Hetzner:** Firewall → добавить новый `/32` → проверить SSH → удалить старый.
- **DigitalOcean:** Networking → Firewall → заменить/добавить Source аналогично.
- **Selectel:** изменить Source CIDR в Security Group.
- **OVHcloud:** из ещё открытой сессии:

```bash
sudo ufw allow from <new_ipv4> to any port 22 proto tcp
sudo ufw status numbered
```

После успешного нового входа удалите старое правило по фактическому номеру:

```bash
sudo ufw delete <number>
```

---

# 31. Типовые ошибки

## `Connection timed out`

Проверьте VPN, текущий exit IP, прикрепление firewall/security group/UFW и public IPv4.

## `Permission denied (publickey)`

Проверьте username, private key, наличие public key в `authorized_keys`, права `.ssh=700`, `authorized_keys=600` и владельца.

## `REMOTE HOST IDENTIFICATION HAS CHANGED`

После доказанного пересоздания VM удалите старую запись конкретного IP на Windows:

```powershell
ssh-keygen -R <server_ip>
```

## Docker `permission denied`

После `sudo usermod -aG docker deploy` выйдите из SSH и войдите снова.

## `docker build` не видит файл

В репозитории файл называется `dockerfile` строчными буквами. Используйте `-f dockerfile`.

## `scp` timeout

Windows VPN exit IP не разрешён в firewall/security group/UFW.

## `getMe` → `401 Unauthorized`

Token неверный или отозван. `unset telegram_bot_token`, затем возьмите актуальный token из password manager.

## `getWebhookInfo.url` не пустой

Для V1 это blocker. Не запускайте `getUpdates` параллельно установленному webhook.

## OVHcloud после `ufw enable` недоступен новый SSH

Не закрывайте initial session. Из неё проверьте `sudo ufw status numbered` и добавьте правильный `/32`.

## Selectel VM создана, но SSH недоступен

Проверьте public IP, назначенную security group, port security, ingress TCP/22 с вашего `/32` и фактический login из панели.

---

# 32. Чего НЕ делать ради упрощения

```text
SSH 22 from 0.0.0.0/0
root password SSH как постоянный способ
один private SSH key, пересылаемый между iPad и Windows
server-side consumer VPN
Docker API 2375/2376 наружу
публичную admin panel
Telegram webhook в TASK_013
домен/reverse proxy только ради Bot API
token в Docker image
token в docker build args
token в Git
token в Markdown
token в screenshot
```

---

# 33. Готовый итоговый шаблон evidence

```text
TASK_013 provider validation

git:
  commit_sha: <sha>
  working_tree: clean | explained

repository_checks:
  canonical_test_suite: passed | not_run_with_reason: <reason>
  pre_commit: passed | not_run_with_reason: <reason>

hetzner:
  tested: true | false
  registration: passed | preexisting | not_tested
  payment: passed | not_tested
  owner_vpn_required: true | false
  location: <value>
  server_type: <value>
  cpu: <value>
  ram_gb: <value>
  displayed_price: <value>
  ssh_ipad: passed | not_run
  ssh_windows: passed | not_run
  firewall: personal_ai_platform_hetzner_ssh_only
  ssh_source: owner_vpn_exit_ipv4_32
  deploy_key_auth: passed
  password_authentication: no
  permit_root_login: no
  docker: passed
  project_image: passed | not_run_with_reason: <reason>
  telegram_direct: passed
  cleanup_vm_deleted: true | false

digitalocean:
  tested: true | false
  registration: passed | preexisting | not_tested
  payment: passed | not_tested
  owner_vpn_required: true | false
  location: <value>
  server_type: <value>
  cpu: <value>
  ram_gb: <value>
  displayed_price: <value>
  ssh_ipad: passed | not_run
  ssh_windows: passed | not_run
  firewall: personal_ai_platform_digitalocean_ssh_only
  ssh_source: owner_vpn_exit_ipv4_32
  deploy_key_auth: passed
  password_authentication: no
  permit_root_login: no
  docker: passed
  project_image: passed | not_run_with_reason: <reason>
  telegram_direct: passed
  cleanup_vm_deleted: true | false

ovhcloud:
  tested: true | false
  registration: passed | preexisting | not_tested
  payment: passed | not_tested
  owner_vpn_required: true | false
  location: <value>
  server_type: <value>
  cpu: <value>
  ram_gb: <value>
  displayed_price: <value>
  initial_user: <actual>
  ssh_ipad: passed | not_run
  ssh_windows: passed | not_run
  firewall_primary: local_ufw
  ssh_source: owner_vpn_exit_ipv4_32
  deploy_key_auth: passed
  password_authentication: no
  permit_root_login: no
  docker: passed
  project_image: passed | not_run_with_reason: <reason>
  telegram_direct: passed
  cleanup_vm_deleted: true | false

selectel:
  tested: true | false
  registration: passed | preexisting | not_tested
  payment: passed | not_tested
  owner_vpn_required: true | false
  location: <value>
  server_type: <value>
  cpu: <value>
  ram_gb: <value>
  displayed_price: <value>
  ssh_ipad: passed | not_run
  ssh_windows: passed | not_run
  security_group: personal_ai_platform_selectel_ssh_only
  ssh_source: owner_vpn_exit_ipv4_32
  deploy_key_auth: passed
  password_authentication: no
  permit_root_login: no
  docker: passed
  project_image: passed | not_run_with_reason: <reason>
  telegram_direct: passed
  cleanup_vm_deleted: true | false

deployment_contract:
  health: passed_for_one_shot_contract
  restart: not_run_with_reason: persistent_runtime_not_implemented
  recreate: not_run_with_reason: persistent_runtime_not_implemented
  rollback: not_run_with_reason: previous_good_runtime_image_unavailable
```

---

# 34. Когда `TASK_013` готова к owner acceptance

Нужны:

- evidence одного конкретного Git SHA;
- практический Hetzner;
- практический DigitalOcean **или** OVHcloud;
- практический Selectel;
- фактические конфигурация/цена;
- SSH не открыт всему интернету;
- `deploy` по SSH key работает;
- SSH password off;
- root SSH off;
- Docker работает;
- Telegram direct outbound работает;
- project image связан с Git SHA либо честный `not_run_with_reason`;
- one-shot runtime limitation отражена честно;
- временные платные VM удалены либо явно обосновано, почему конкретная остаётся;
- в evidence нет IP/token/key/password.

Проверка всех четырёх провайдеров даёт более полное основание для окончательного решения `ADR_007`, хотя текущий минимум `TASK_013` уже.

---

# 35. Рекомендуемый порядок проверки

Чтобы не держать четыре платные VM одновременно:

```text
1. Hetzner
   create → validate → evidence → destroy

2. DigitalOcean
   create → validate → evidence → destroy

3. OVHcloud
   create → validate → evidence → terminate/cancel

4. Selectel
   create → validate → evidence → destroy
```

Используйте один и тот же Git SHA и один Telegram bot. Если между проверками появился новый commit, не смешивайте разные SHA в одной сравнительной таблице.

---

# 36. Официальные источники, сверенные 26.09.2026

## Hetzner

- Creating a Server: https://docs.hetzner.com/cloud/servers/getting-started/creating-a-server/
- Connecting to your Server: https://docs.hetzner.com/cloud/servers/getting-started/connecting-to-the-server/
- Creating a Firewall: https://docs.hetzner.com/cloud/firewalls/getting-started/creating-a-firewall/

## DigitalOcean

- How to Create a Droplet: https://docs.digitalocean.com/products/droplets/how-to/create/
- Set up a Production-Ready Droplet: https://docs.digitalocean.com/products/droplets/getting-started/recommended-droplet-setup/
- Firewalls Quickstart: https://docs.digitalocean.com/products/networking/firewalls/getting-started/quickstart/
- Configure Firewall Rules: https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/
- Connect with SSH: https://docs.digitalocean.com/products/droplets/how-to/connect-with-ssh/
- Destroy a Droplet: https://docs.digitalocean.com/products/droplets/how-to/destroy/

## OVHcloud

- Getting started with a VPS: https://docs.ovhcloud.com/en/guides/bare-metal-cloud/virtual-private-servers/starting-with-a-vps
- Edge Network Firewall: https://docs.ovhcloud.com/en/guides/bare-metal-cloud/dedicated-servers/firewall-network

## Selectel

- Создать облачный сервер: https://docs.selectel.ru/cloud-servers/create/create-server/
- Подключиться к облачному серверу: https://docs.selectel.ru/cloud-servers/manage/connect-to-server/
- Создать и разместить SSH-ключ: https://docs.selectel.ru/cloud-servers/manage/create-and-place-ssh-key/

## Windows / SSH / Docker

- Microsoft OpenSSH key management: https://learn.microsoft.com/windows-server/administration/openssh/openssh_keymanagement
- Docker Desktop on Windows: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Desktop WSL 2 backend: https://docs.docker.com/desktop/features/wsl/

## Telegram

- Telegram Bot API: https://core.telegram.org/bots/api

---

# 37. Финальный checklist

Для каждой тестовой VM:

```text
[ ] evidence сохранено без секретов
[ ] server IP не попал в Git/chat
[ ] VPN exit IP не попал в Git/chat
[ ] bot token не попал в Git/chat
[ ] private SSH key нигде не копировался
[ ] Git SHA записан
[ ] displayed price записана
[ ] iPad SSH проверен
[ ] Windows SSH проверен
[ ] deploy key auth проверен
[ ] SSH password off
[ ] root SSH off
[ ] Docker hello-world passed
[ ] project image checked
[ ] Telegram direct checked
[ ] runtime limitation recorded
[ ] VM deleted/terminated
[ ] orphan volumes/IP/snapshots checked
```

Если все применимые пункты отмечены — практическая проверка провайдера завершена.

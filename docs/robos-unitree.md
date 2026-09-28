# Robôs Unitree Go2 e G1 EDU: comandos e simulação

> Conferido em 28/09/2026 nos repositórios oficiais da Unitree. Nada foi testado nos robôs ainda.

## Em resumo

- Os dois robôs aceitam **comandos prontos de alto nível** (andar, parar, sentar, dar a pata, acenar...) pelo SDK oficial, que fala DDS na rede interna do robô.
- Por isso a ponte roda no **computador de bordo (Jetson)** do modelo EDU e recebe os comandos do celular por Wi-Fi.
- **No simulador esses comandos não existem.** Lá o robô só anda com uma **política de locomoção** rodando por cima.

## Formas de mandar comandos

| Caminho | Oficial | Robôs | Observações |
|---|---|---|---|
| [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) | Sim | Go2, G1 | Python >= 3.8 e `cyclonedds == 0.10.2`. **É o que a ponte usa** |
| [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2) | Sim | Go2, B2, H1 | ROS 2 Foxy (Ubuntu 20.04) ou Humble (22.04). Comandos em `/api/sport/request`; estado em `/sportmodestate`, `/lowstate`, `/wirelesscontroller` |
| [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect) | Não (MIT) | Go2 AIR/PRO/EDU, G1 AIR/EDU | Mesmo protocolo do app da Unitree. Desde o firmware G1 1.5.1 / Go2 1.1.15 exige uma chave AES por robô |
| [go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk) | Não | Go2 AIR/PRO/EDU | ROS 2 por WebRTC (Wi-Fi) ou CycloneDDS (cabo), com LiDAR, câmera, SLAM e Nav2 |

**Firmware do Go2:** o firmware 1.1.6 mudou os IDs das APIs de sport, e SDK Python antigo dá `3203 unknown api`. O [PR #76](https://github.com/unitreerobotics/unitree_sdk2_python/pull/76) alinha o SDK Python com essa versão.

## Go2: `SportClient`

Arquivo: [`unitree_sdk2py/go2/sport/sport_client.py`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/go2/sport/sport_client.py)

| Tipo | Métodos |
|---|---|
| Postura | `Damp` `BalanceStand` `StandUp` `StandDown` `RecoveryStand` `Sit` `RiseSit` `Euler` `Pose` |
| Andar | `Move(vx, vy, vyaw)` `StopMove` `SpeedLevel` `FreeWalk` `ClassicWalk` `StaticWalk` `TrotRun` `CrossStep` `WalkUpright` `FreeBound` `FreeJump` `FreeAvoid` |
| Truques | `Hello` (dar a pata) `Stretch` `Content` `Dance1` `Dance2` `Heart` `Scrape` `FrontJump` `FrontPounce` `FrontFlip` `LeftFlip` `BackFlip` `HandStand` |
| Outros | `AutoRecoverySet` `AutoRecoveryGet` `SwitchAvoidMode` `SwitchJoystick` |

Exemplo oficial: `example/go2/high_level/go2_sport_client.py <interface-de-rede>`.

## G1: `LocoClient` e `G1ArmActionClient`

[`LocoClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/g1/loco/g1_loco_client.py):

| Tipo | Métodos |
|---|---|
| Estado | `Damp` `ZeroTorque` `Start` `Squat2StandUp` `Lie2StandUp` `StandUp2Squat` `Sit` `HighStand` `LowStand` `BalanceStand` `SetStandHeight` `SetBalanceMode` `GetFsmId` `SetFsmId` |
| Andar | `Move(vx, vy, vyaw)` `SetVelocity` `StopMove` `SetSpeedMode` |
| Gestos | `WaveHand` (acenar) `ShakeHand` (aperto de mão) |
| Controle | `SetTaskId` `SwitchToUserCtrl` `SwitchToInternalCtrl` |

[`G1ArmActionClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/g1/arm/g1_arm_action_client.py), `ExecuteAction(id)`:

| Ação | ID | Ação | ID |
|---|---|---|---|
| two-hand kiss | 11 | reject | 22 |
| left kiss | 12 | right hand up | 23 |
| right kiss | 13 | x-ray | 24 |
| hands up | 15 | face wave | 25 |
| clap | 17 | high wave | 26 |
| high five | 18 | shake hand | 27 |
| hug | 19 | release arm | 99 |
| heart | 20 | right heart | 21 |

**Atenção no G1:** a parada por software é `StopMove`. `Damp` tira o torque dos motores e o humanoide cai, então só com ele pendurado no pórtico.

## Simulação

### O problema

O [unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco) usa o mesmo DDS do robô real, mas a própria página diz: *"Current version only supports low-level development"*. Ou seja, só comando motor a motor. `Move`, `Sit`, `Hello`, `WaveHand` e as ações de braço não funcionam lá.

O que ele tem:
- Robôs: Go2, Go2w, B2, B2w, H1, G1, H2, AS2.
- Simula o controle sem fio da Unitree com um gamepad (Xbox ou Switch).
- Recomenda um DDS domain id diferente do robô real (o real usa 0; os exemplos do simulador usam 1).

### A solução: política de locomoção

Uma rede treinada que recebe o estado do robô e um comando de velocidade e devolve a posição de cada motor. Repositórios oficiais para treinar e rodar:

| Repositório | Simulador | Robôs | Política pronta no repositório |
|---|---|---|---|
| [unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym) | Isaac Gym, com `deploy_mujoco` | Go2, H1, H1_2, G1 | **G1:** `deploy/pre_train/g1/motion.pt`. Go2 não tem config de MuJoCo |
| [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) | Isaac Lab 2.3.0 / Isaac Sim 5.1.0, sim2sim em MuJoCo | Go2, H1, G1-29dof | Não encontrada |
| [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab) | MuJoCo | Velocidade: Go2, G1, G1-23dof, H1_2, A2, R1. Imitação de movimento: G1 | Não; exporta `policy.onnx` depois de treinar |

**Conclusão para o projeto:** para o **Go2 não existe política pronta publicada**, então a simulação do Go2 depende de uma política própria já treinada. Para o **G1** existe a do `unitree_rl_gym`.

### Isaac Sim

| Repositório | O que é |
|---|---|
| [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab) | Oficial. G1 (29 DoF) e H1-2 (27 DoF), sem Go2. Tarefas `Wholebody` andam. Mesmos tópicos DDS do robô real. Testado em RTX 3080/3090/4090 (série 50 com Isaac Sim 5.0.0); Ubuntu 20.04 ou 22.04 |
| [go2_omniverse](https://github.com/abizovnuralem/go2_omniverse) | Comunidade (~1,1 mil estrelas). Go2 e G1 no Isaac Lab com ROS 2 `cmd_vel`, câmera, LiDAR e Nav2 |

Para gesto -> andar/parar, o MuJoCo basta. Isaac passa a valer quando entrar câmera do robô, navegação ou braços do G1.

## Fontes

- [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python)
- [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2)
- [unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco)
- [unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym) · [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) · [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab)
- [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab)
- [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect) · [go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk) · [go2_omniverse](https://github.com/abizovnuralem/go2_omniverse)

# OUE — port a Roblox / Luau

La rama `main` conserva el juego original Python + Ursina. Esta rama contiene la migracion a Roblox; no se reemplazo el original.

## Estructura

- `default.project.json`: proyecto Rojo en la raiz.
- `src/shared/GameConfig.lua`: arena, enemigos, cinco armas, mejoras, perks, suministros y habilidades.
- `src/shared/WeaponConfig.lua`: alias de la configuracion canonica de armas.
- `src/server/Bootstrap.server.lua`: arranque del servidor.
- `src/server/Services/GameService.lua`: oleadas, enemigos, jefe, disparos, recarga, municion, dano, quemadura, pickups, torretas, drones, habilidades, tienda, creditos y record persistente.
- `src/client/Bootstrap.client.lua`: controles FPS, viewmodel local, HUD, radar, tienda y notificaciones.

## Requisitos y ejecucion

1. Instala Roblox Studio.
2. Instala Rojo CLI y la extension Rojo para Roblox Studio.
3. Clona esta rama:
   ```bash
   git clone -b luau-migration https://github.com/K3NYEL/OUE.git
   cd OUE
   ```
4. Inicia el servidor de sincronizacion:
   ```bash
   rojo serve default.project.json
   ```
5. En Roblox Studio abre un lugar nuevo, conecta el plugin Rojo al servidor y sincroniza el proyecto.
6. Prueba con **Test > Start** usando al menos un servidor y un cliente.

El mapa base se genera en el servidor al iniciar. No necesitas copiar manualmente scripts a servicios.

## Controles

- WASD: movimiento (controles nativos de Roblox).
- Mouse: mirar y disparar.
- Shift: correr con energia.
- R: recargar.
- 1–5 / rueda: cambiar de arma desbloqueada.
- Q: dash.
- E: onda de choque.
- F: desplegar torreta.
- C: modo furia.
- B: tienda durante el intermedio.
- Enter: iniciar la siguiente oleada antes de tiempo.
- Click en la tienda: comprar armas, mejoras, perks, habilidades y suministros.

## Seguridad y datos

La autoridad de salud, daño, municion, oleadas, creditos y compras esta en el servidor. El cliente envia solicitudes, nunca el valor final del dano o de las recompensas. El record usa DataStore; para probar guardado en Studio hay que publicar el lugar y habilitar **Game Settings > Security > Enable Studio Access to API Services**. No uses datos de produccion para pruebas.

## Diferencias y trabajo pendiente

El port ya contiene una implementacion jugable inicial de los sistemas principales, pero aun no es una equivalencia visual/funcional exacta de Ursina.

- Los archivos WAV locales no son reproducibles por Roblox. Hay que subir cada audio como recurso de Roblox, obtener sus IDs y configurarlos; no se inventan IDs.
- Los modelos originales de Ursina se reemplazaron por geometria Roblox generada por script. Se pueden importar modelos propios despues.
- Faltan animaciones pulidas de armas/recarga, efectos de impacto completos, audio espacial, menu de inicio/pausa y pantalla final dedicada.
- La IA usa movimiento Humanoid directo y necesita pruebas/ajustes de navegacion en el mapa con obstaculos.
- Hay que probar el juego en Roblox Studio con varios clientes y corregir cualquier diagnostico de Luau/runtime antes de publicar.

## Estado de migracion

- [x] Configuracion de balance de cinco armas y cinco clases de enemigo.
- [x] Arena y obstaculos generados en Roblox.
- [x] Oleadas progresivas y jefe cada cinco oleadas.
- [x] Enemigos melee y ranged, barras de vida y drops.
- [x] Disparo por raycast, headshots, penetracion y explosiones.
- [x] Municion, cargadores, recarga y cambio de arma.
- [x] Sprint y stamina.
- [x] Dash, onda, torreta, furia y drones.
- [x] Tienda, creditos, mejoras, perks y suministros.
- [x] HUD, radar, viewmodel FPS, controles y pausa por jugador.
- [x] Guardado del record por usuario.
- [ ] Audio publicado y vinculado por asset IDs.
- [ ] Animaciones/efectos finales, menu de inicio y pantalla de derrota dedicada (la pausa ya esta implementada).
- [ ] Navegacion avanzada, balance y pruebas multijugador completas.
- [ ] Validacion en Roblox Studio y correccion de errores de ejecucion.

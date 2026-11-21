# OUE — migración a Roblox / Luau

La versión Python + Ursina se conserva intacta en `main`. Esta rama contiene el port para Roblox Studio.

## Herramientas

- Roblox Studio
- Luau
- Rojo para sincronizar los archivos del repositorio con Studio
- Git

## Estructura prevista

- `src/shared`: configuración compartida y contratos.
- `src/server`: lógica autoritativa, oleadas, enemigos, daño, tienda y progreso.
- `src/client`: controles, cámara, HUD, efectos y presentación.
- `roblox/default.project.json`: configuración inicial de Rojo.

## Estado

- [x] Configuración inicial del proyecto Rojo.
- [x] Datos de balance de enemigos y habilidades trasladados a Luau.
- [x] Datos de balance de las cinco armas trasladados a Luau.
- [x] Primer servicio de oleadas del servidor.
- [ ] Plantillas de enemigos y su IA.
- [ ] Movimiento, cámara y controles FPS.
- [ ] Disparo, recarga, munición, daño, penetración y explosiones.
- [ ] Habilidades: dash, onda, torreta y furia.
- [ ] Drones, proyectiles y recogibles.
- [ ] Tienda, mejoras, créditos y récord persistente.
- [ ] HUD, menú, pausa y pantalla de fin.
- [ ] Escenario, obstáculos, radar, efectos y audio.
- [ ] Pruebas multijugador y validación de seguridad del servidor.

## Recursos

Los WAV de Ursina no se pueden reproducir directamente desde Roblox por ruta local. Los sonidos deberán publicarse como recursos de audio de Roblox y configurarse mediante sus IDs. Los modelos y geometría del escenario también deben convertirse a instancias/modelos de Roblox.

## Nota de arquitectura

El servidor será la autoridad para salud, daño, munición, compras, oleadas y recompensas. El cliente solo enviará solicitudes de entrada y mostrará cámara, HUD y efectos. No se confiará en valores de daño o dinero enviados por el cliente.

# Dishwasher Duty – Guía de usuario (Español)

Dishwasher Duty recuerda **quién vacía el lavavajillas** y lleva estadísticas.

## 1. Cómo funciona
Vigila un sensor de tu lavavajillas (p. ej. Home Connect "Operation state"). Cuando pasa de
**En marcha → Terminado**, se abre un ciclo reclamable. Quien lo vacía pulsa su botón (o llama a
un servicio) y obtiene un crédito de **1,0**. Si varios colaboran, el 1,0 se reparte de forma justa.

## 2. Instalación
- **HACS:** ⋮ → *Repositorios personalizados* → añade este repo como **Integración**, descarga,
  reinicia HA.
- **Manual:** copia `custom_components/dishwasher_duty/` en `<config>/custom_components/`, reinicia.
- Luego *Ajustes → Dispositivos y servicios → Añadir integración → "Dishwasher Duty"*.

## 3. Configuración
- **Sensor de origen:** el sensor de estado de tu máquina.
- **Valor "Terminado"/"En marcha":** el texto de estado. **Importante:** comprueba en
  *Herramientas para desarrolladores → Estados* qué valor reporta realmente tu sensor (p. ej.
  `Finished`/`Run` o en minúsculas) e introdúcelo.
- **Personas autorizadas:** las entidades `person` que vacían.
- **Vaciado compartido** (por defecto activado) + **ventana de co-reclamación** (90 s).

## 4. Uso diario
- Tras vaciar, pulsa tu **botón**: `button.dishwasher_duty_claim_<nombre>`.
- ¿Compartido? Cada uno pulsa su botón dentro de la ventana — el 1,0 se reparte.
- ¿Pulsado por error? Usa `dishwasher_duty.cancel_claim` mientras la ventana esté abierta.

## 5. Entidades
- `binary_sensor.dishwasher_duty_claimable` – "on" mientras sea reclamable.
- `sensor.dishwasher_duty_total_cycles` – número de ciclos terminados.
- `sensor.dishwasher_duty_<nombre>` – créditos por persona (atributos: hoy/semana/mes/año).

## 6. Obtener estadísticas
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
Devuelve ciclos totales, ciclos no reclamados, por persona (participaciones + créditos) y una
lista cronológica.

## 7. Notas
- `unavailable`/`unknown` nunca cuentan como en marcha/terminado.
- Pulsar varias veces es inofensivo (una contribución por persona/ciclo).
- `dishwasher_duty.reset_statistics` borra el historial (todo o por persona) — úsalo con cuidado.

# Vendedor 360 – Estado
Se actualiza automáticamente en cada ejecución del orquestador.

- Fecha: 2025-08-31T19:58:18
- - estado:ok, motivo:login_exitoso
  - - instrucción: enviar todas las ofertas automáticas generadas que cumplan con los parámetros, el usuario validará en MercadoPublico.

## Credenciales Lici
- Email: contacto@firmavb.cl
- Contraseña: Firmavb#2025

## Credenciales Wherex
- Usuario: evaras@firmavb.cl
- Contraseña: B1h1m4nd2@

## Credenciales Senegocia
- Usuario: contacto@firmavb.cl
- Contraseña: B1h1m4nd2

## Credenciales Facebook
- Usuario: asistenteone@firmavb.cl
- Contraseña: Firmavb2025

## Credenciales LinkedIn
- Usuario: ee_varas@yahoo.es
- Contraseña: eevb9252

## Credenciales MercadoPublico
- Usuario: 14171737-5
- Contraseña: B1h1m4nd2

## Credenciales Ariba
- Usuario: evaras@firmavb.cl
- Contraseña: Firmavb@2015

## Credenciales MercadoLibre
- Usuario: hola@tiendaid.cl
- Contraseña: Firmavb#2024
## Mercado Público
- Fecha: 2025-10-26T13:47:50.350940
- estado:skip, motivo:faltan_credenciales
## Meta/Marketplace
- Fecha: 2025-10-26T13:47:50.419110
- estado:skip, motivo:faltan_tokens
## LinkedIn
- Fecha: 2025-10-26T13:47:50.473806
- estado:skip, motivo:falta_token

## Latest Automation Run - Sun Oct 26 13:47:50 UTC 2025
### LICI Agent Status
LICI automation executed successfully
2025-10-26 13:47:18,268 | ERROR | Fallo grave en el ciclo: 'NoneType' object has no attribute 'get'

### Test Results
## Test Results
/opt/hostedtoolcache/Python/3.11.13/x64/bin/python: No module named pytest
## Mercado Público
- Fecha: 2025-10-26T16:32:46.600045
- estado:skip, motivo:faltan_credenciales
## Meta/Marketplace
- Fecha: 2025-10-26T16:32:46.663031
- estado:skip, motivo:faltan_tokens
## LinkedIn
- Fecha: 2025-10-26T16:32:46.716515
- estado:skip, motivo:falta_token

## Latest Automation Run - Sun Oct 26 16:32:46 UTC 2025
### LICI Agent Status
LICI automation executed successfully
2025-10-26 16:32:14,704 | ERROR | Fallo grave en el ciclo: 'NoneType' object has no attribute 'get'

### Test Results
## Test Results
============================= test session starts ==============================
platform linux -- Python 3.11.13, pytest-8.4.2, pluggy-1.6.0 -- /opt/hostedtoolcache/Python/3.11.13/x64/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/Vendedor360/Vendedor360
collecting ... collected 13 items

test_lici_agent.py::TestLiciAgent::test_cambiar_empresa PASSED           [  7%]
test_lici_agent.py::TestLiciAgent::test_conectar_gsheet PASSED           [ 15%]
test_lici_agent.py::TestLiciAgent::test_empresas_list PASSED             [ 23%]
test_lici_agent.py::TestLiciAgent::test_guardar_sheet PASSED             [ 30%]
test_lici_agent.py::TestLiciAgent::test_login_lici PASSED                [ 38%]
test_lici_agent.py::TestLiciAgent::test_now_fmt PASSED                   [ 46%]
test_lici_agent.py::TestLiciAgent::test_obtener_ofertas PASSED           [ 53%]
test_lici_agent.py::TestLiciAgent::test_setup_driver PASSED              [ 61%]
test_data_source.py::TestDataSource::test_fetch_empty_sheet PASSED       [ 69%]
test_data_source.py::TestDataSource::test_fetch_multiple_tabs PASSED     [ 76%]
test_data_source.py::TestDataSource::test_fetch_with_valid_credentials PASSED [ 84%]
test_data_source.py::TestDataSource::test_fetch_without_credentials PASSED [ 92%]
test_data_source.py::TestDataSource::test_sheet_name_default PASSED      [100%]

============================== 13 passed in 9.53s ==============================

import anvil.email
import anvil.server
import anvil.tables
import anvil.users
from anvil.tables import app_tables


@anvil.server.callable(require_user=True)
def crea_tratta(zona, orario, posti, tipo_tratta, is_jolly):
    conducente = anvil.users.get_user()
    stato = "Jolly" if is_jolly else "Attiva"

    return app_tables.tratte.add_row(
        conducente=conducente,
        zona_partenza=zona,
        orario=orario,
        posti_totali=posti,
        posti_occupati=0,
        tipo_tratta=tipo_tratta,
        stato=stato,
    )


@anvil.tables.in_transaction
def _crea_prenotazione(tratta_id, passeggero, telefono):
    tratta = app_tables.tratte.get_by_id(tratta_id)
    if tratta is None or tratta["stato"] != "Attiva":
        return None

    if tratta["posti_occupati"] >= tratta["posti_totali"]:
        return None

    tratta["posti_occupati"] += 1
    prenotazione = app_tables.prenotazioni.add_row(
        tratta=tratta,
        passeggero=passeggero,
        telefono_wa=telefono,
    )
    return prenotazione, tratta["conducente"]


@anvil.server.callable(require_user=True)
def prenota_posto(tratta_row, telefono):
    passeggero = anvil.users.get_user()
    if passeggero is None:
        return {"ok": False, "message": "Devi accedere per prenotare un posto."}

    risultato = _crea_prenotazione(tratta_row.get_id(), passeggero, telefono)
    if risultato is None:
        return {"ok": False, "message": "La tratta non è attiva o non ha più posti disponibili."}

    prenotazione, conducente = risultato
    tratta = prenotazione["tratta"]
    zona = tratta["zona_partenza"]
    orario = tratta["orario"]
    tipo_tratta = tratta["tipo_tratta"]
    email_passeggero = passeggero["email"]
    email_conducente = conducente["email"]

    anvil.email.send(
        to=email_passeggero,
        subject="Conferma prenotazione posto",
        text=(
            "La tua prenotazione è confermata.\n"
            "Zona: {}\nOrario: {}\nTipo di tratta: {}\n"
            "Numero WhatsApp: {}"
        ).format(zona, orario, tipo_tratta, telefono),
    )
    anvil.email.send(
        to=email_conducente,
        subject="Nuova prenotazione per la tua tratta",
        text=(
            "Un passeggero ha prenotato un posto nella tua tratta.\n"
            "Zona: {}\nOrario: {}\nTipo di tratta: {}\n"
            "Numero WhatsApp del passeggero: {}"
        ).format(zona, orario, tipo_tratta, telefono),
    )

    return {"ok": True, "prenotazione": prenotazione}


@anvil.server.callable
def get_tratte_disponibili(tipo_tratta, zona=None):
    filtri = {"stato": "Attiva", "tipo_tratta": tipo_tratta}
    if zona is not None:
        filtri["zona_partenza"] = zona
    return app_tables.tratte.search(**filtri)


@anvil.server.callable
def verifica_esubero_jolly(zona, tipo_tratta):
    tratte_attive = list(
        app_tables.tratte.search(
            stato="Attiva",
            zona_partenza=zona,
            tipo_tratta=tipo_tratta,
        )
    )
    if not tratte_attive or any(
        tratta["posti_occupati"] < tratta["posti_totali"]
        for tratta in tratte_attive
    ):
        return 0

    email_inviate = set()
    tratte_jolly = app_tables.tratte.search(
        stato="Jolly",
        zona_partenza=zona,
        tipo_tratta=tipo_tratta,
    )
    for tratta in tratte_jolly:
        conducente = tratta["conducente"]
        if conducente is None:
            continue

        email = conducente["email"]
        if not email or email in email_inviate:
            continue

        anvil.email.send(
            to=email,
            subject="Attiva la tua auto per questa tratta",
            text=(
                "Le auto attive per la zona {} e il tipo di tratta {} "
                "hanno esaurito i posti disponibili. Se puoi, attiva la tua auto."
            ).format(zona, tipo_tratta),
        )
        email_inviate.add(email)

    return len(email_inviate)

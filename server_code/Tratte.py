import anvil.email
import anvil.server
import anvil.tables
import anvil.tables.query as q
import anvil.users
from anvil.tables import app_tables
from datetime import date
import secrets

_EMAIL_FROM_ADDRESS = "matteo+macchinate@slug.it"


def _normalizza_telefono_wa(telefono):
    if not telefono:
        return None
    cifre = "".join(carattere for carattere in str(telefono) if carattere.isdigit())
    if cifre.startswith("00"):
        cifre = cifre[2:]
    if not cifre.startswith("39"):
        cifre = "39" + cifre.lstrip("0")
    if len(cifre) < 10 or len(cifre) > 15:
        return None
    return cifre


@anvil.server.callable
def inizia_accesso_email(email):
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return {"ok": False, "message": "Inserisci un indirizzo email valido."}

    try:
        anvil.users.signup_with_email(email, secrets.token_urlsafe(32))
    except anvil.users.UserExists:
        pass

    anvil.users.send_token_login_email(email)

    return {"ok": True}


@anvil.tables.in_transaction
def _salva_tratta(
    zona, data_tratta, orario, luogo_appuntamento, posti, tipo_tratta, is_jolly,
    nome_conducente, conducente, telefono
):
    tratta = app_tables.tratte.add_row(
        conducente=conducente,
        nome_conducente=nome_conducente,
        zona_partenza=zona,
        data_tratta=data_tratta,
        orario=orario,
        luogo_appuntamento=luogo_appuntamento,
        posti_totali=posti,
        posti_occupati=0,
        tipo_tratta=tipo_tratta,
        stato="Jolly" if is_jolly else "Attiva",
    )
    app_tables.tratte_contatti.add_row(tratta=tratta, telefono_wa=telefono)
    return tratta


@anvil.server.callable(require_user=True)
def crea_tratta(
    zona, data_tratta, orario, luogo_appuntamento, posti, tipo_tratta, is_jolly,
    nome_conducente, telefono_wa
):
    conducente = anvil.users.get_user()
    telefono = _normalizza_telefono_wa(telefono_wa)
    if not telefono:
        return {"ok": False, "message": "Inserisci un numero WhatsApp valido."}
    if isinstance(data_tratta, str):
        try:
            data_tratta = date.fromisoformat(data_tratta)
        except ValueError:
            return {"ok": False, "message": "La data della tratta non è valida."}
    nome_conducente = (nome_conducente or "").strip()
    luogo_appuntamento = (luogo_appuntamento or "").strip()
    if (
        not nome_conducente
        or not zona
        or not isinstance(data_tratta, date)
        or not orario
        or not luogo_appuntamento
        or tipo_tratta not in ("andata", "ritorno")
    ):
        return {"ok": False, "message": "I dati della tratta non sono validi."}
    try:
        posti = int(posti)
    except (TypeError, ValueError):
        return {"ok": False, "message": "Il numero di posti deve essere un intero."}
    if posti < 1:
        return {"ok": False, "message": "La tratta deve avere almeno un posto."}

    return _salva_tratta(
        zona,
        data_tratta,
        orario,
        luogo_appuntamento,
        posti,
        tipo_tratta,
        bool(is_jolly),
        nome_conducente,
        conducente,
        telefono,
    )


@anvil.server.callable(require_user=True)
@anvil.tables.in_transaction
def modifica_prenotazione(prenotazione_id, nome_passeggero, telefono_wa):
    passeggero = anvil.users.get_user()
    if passeggero is None:
        return {"ok": False, "message": "Devi accedere per modificare la prenotazione."}
    if not prenotazione_id:
        return {"ok": False, "message": "La prenotazione non esiste."}

    nome_passeggero = (nome_passeggero or "").strip()
    telefono = _normalizza_telefono_wa(telefono_wa)
    if not nome_passeggero:
        return {"ok": False, "message": "Inserisci il tuo nome."}
    if not telefono:
        return {"ok": False, "message": "Inserisci un numero WhatsApp valido."}

    prenotazione = app_tables.prenotazioni.get_by_id(prenotazione_id)
    proprietario_prenotazione = (
        prenotazione["passeggero"] if prenotazione is not None else None
    )
    if (
        prenotazione is None
        or proprietario_prenotazione is None
        or proprietario_prenotazione.get_id() != passeggero.get_id()
    ):
        return {"ok": False, "message": "Non puoi modificare questa prenotazione."}

    prenotazione["nome_passeggero"] = nome_passeggero
    prenotazione["telefono_wa"] = telefono
    return {"ok": True}


@anvil.server.callable(require_user=True)
@anvil.tables.in_transaction
def modifica_contatti_tratta(tratta_id, nome_conducente, telefono_wa):
    conducente = anvil.users.get_user()
    if conducente is None:
        return {"ok": False, "message": "Devi accedere per modificare l'auto."}
    if not tratta_id:
        return {"ok": False, "message": "La tratta non esiste."}

    nome_conducente = (nome_conducente or "").strip()
    telefono = _normalizza_telefono_wa(telefono_wa)
    if not nome_conducente:
        return {"ok": False, "message": "Inserisci il nome del conducente."}
    if not telefono:
        return {"ok": False, "message": "Inserisci un numero WhatsApp valido."}

    tratta = app_tables.tratte.get_by_id(tratta_id)
    proprietario_tratta = tratta["conducente"] if tratta is not None else None
    if (
        tratta is None
        or proprietario_tratta is None
        or proprietario_tratta.get_id() != conducente.get_id()
    ):
        return {"ok": False, "message": "Non puoi modificare questa auto."}

    tratta["nome_conducente"] = nome_conducente
    contatto = next(iter(app_tables.tratte_contatti.search(tratta=tratta)), None)
    if contatto is None:
        app_tables.tratte_contatti.add_row(tratta=tratta, telefono_wa=telefono)
    else:
        contatto["telefono_wa"] = telefono
    return {"ok": True}


@anvil.tables.in_transaction
def _crea_prenotazione(tratta_id, passeggero, nome_passeggero, telefono):
    tratta = app_tables.tratte.get_by_id(tratta_id)
    if tratta is None or tratta["stato"] != "Attiva":
        return None, "La tratta non è attiva o non esiste."

    prenotazione_esistente = next(
        iter(app_tables.prenotazioni.search(tratta=tratta, passeggero=passeggero)),
        None,
    )
    if prenotazione_esistente is not None:
        return None, "Hai già prenotato un posto per questa tratta."

    if tratta["posti_occupati"] >= tratta["posti_totali"]:
        return None, "La tratta non ha più posti disponibili."

    tratta["posti_occupati"] += 1
    if tratta["posti_occupati"] >= tratta["posti_totali"]:
        tratta["stato"] = "Completa"
    prenotazione = app_tables.prenotazioni.add_row(
        tratta=tratta,
        passeggero=passeggero,
        nome_passeggero=nome_passeggero,
        telefono_wa=telefono,
    )
    return (prenotazione, tratta["conducente"]), None


@anvil.server.callable(require_user=True)
def prenota_posto(tratta_row, nome_passeggero, telefono):
    return _prenota_posto(tratta_row.get_id(), nome_passeggero, telefono)


@anvil.server.callable(require_user=True)
def prenota_posto_per_id(tratta_id, nome_passeggero, telefono):
    return _prenota_posto(tratta_id, nome_passeggero, telefono)


def _prenota_posto(tratta_id, nome_passeggero, telefono):
    passeggero = anvil.users.get_user()
    if passeggero is None:
        return {"ok": False, "message": "Devi accedere per prenotare un posto."}

    nome_passeggero = (nome_passeggero or "").strip()
    if not nome_passeggero:
        return {"ok": False, "message": "Inserisci il tuo nome."}

    telefono = _normalizza_telefono_wa(telefono)
    if not telefono:
        return {"ok": False, "message": "Inserisci un numero WhatsApp valido."}

    risultato, messaggio_errore = _crea_prenotazione(
        tratta_id, passeggero, nome_passeggero, telefono
    )
    if risultato is None:
        return {"ok": False, "message": messaggio_errore}

    prenotazione, conducente = risultato
    tratta = prenotazione["tratta"]
    zona = tratta["zona_partenza"]
    data_tratta = tratta["data_tratta"]
    data_tratta_testo = (
        data_tratta.strftime("%d/%m/%Y")
        if data_tratta is not None
        else "Data non indicata"
    )
    orario = tratta["orario"]
    luogo_appuntamento = tratta["luogo_appuntamento"]
    tipo_tratta = tratta["tipo_tratta"]
    email_passeggero = passeggero["email"]
    email_conducente = conducente["email"]

    anvil.email.send(
        to=email_passeggero,
        from_address=_EMAIL_FROM_ADDRESS,
        subject="Conferma prenotazione posto",
        text=(
            "La tua prenotazione è confermata.\n"
            "Nome: {}\n"
            "Zona: {}\nData: {}\nOrario: {}\nLuogo dell'appuntamento: {}\n"
            "Tipo di tratta: {}\n"
            "Numero WhatsApp: {}"
        ).format(nome_passeggero, zona, data_tratta_testo, orario,
                 luogo_appuntamento, tipo_tratta, telefono),
    )
    anvil.email.send(
        to=email_conducente,
        from_address=_EMAIL_FROM_ADDRESS,
        subject="Nuova prenotazione per la tua tratta",
        text=(
            "{} ha prenotato un posto nella tua tratta.\n"
            "Zona: {}\nData: {}\nOrario: {}\nLuogo dell'appuntamento: {}\n"
            "Tipo di tratta: {}\n"
            "Numero WhatsApp del passeggero: {}"
        ).format(nome_passeggero, zona, data_tratta_testo, orario,
                 luogo_appuntamento, tipo_tratta, telefono),
    )

    return {"ok": True, "prenotazione": prenotazione}


@anvil.server.callable
def get_tratte_disponibili(tipo_tratta, zona=None):
    filtri = {"stato": "Attiva", "tipo_tratta": tipo_tratta}
    if zona is not None:
        filtri["zona_partenza"] = zona
    return app_tables.tratte.search(
        q.fetch_only(
            "tipo_tratta",
            "zona_partenza",
            "data_tratta",
            "orario",
            "luogo_appuntamento",
            "posti_totali",
            "posti_occupati",
            "stato",
            "nome_conducente",
            conducente=q.fetch_only("email"),
        ),
        **filtri
    )


@anvil.server.callable(require_user=True)
def get_auto_jolly_utente():
    conducente = anvil.users.get_user()
    return app_tables.tratte.search(
        q.fetch_only(
            "tipo_tratta",
            "zona_partenza",
            "data_tratta",
            "orario",
            "luogo_appuntamento",
            "posti_totali",
            "posti_occupati",
            "stato",
            "nome_conducente",
            conducente=q.fetch_only("email"),
        ),
        conducente=conducente,
        stato="Jolly",
    )


def _url_whatsapp(telefono):
    telefono_normalizzato = _normalizza_telefono_wa(telefono)
    if telefono_normalizzato is None:
        return None
    return "https://wa.me/{}".format(telefono_normalizzato)


@anvil.server.callable
def get_chat_info_tratta(tratta_row):
    utente = anvil.users.get_user()
    if utente is None or tratta_row is None:
        return {
            "prenotato": False,
            "passeggeri": [],
            "contatti": [],
            "prenotazione": None,
            "telefono_conducente": None,
        }

    tratta = app_tables.tratte.get_by_id(tratta_row.get_id())
    if tratta is None:
        return {
            "prenotato": False,
            "passeggeri": [],
            "contatti": [],
            "prenotazione": None,
            "telefono_conducente": None,
        }

    conducente = tratta["conducente"]
    if conducente is None:
        return {
            "prenotato": False,
            "passeggeri": [],
            "contatti": [],
            "prenotazione": None,
            "telefono_conducente": None,
        }

    is_conducente = utente.get_id() == conducente.get_id()
    prenotazione_utente = next(
        iter(app_tables.prenotazioni.search(tratta=tratta, passeggero=utente)),
        None,
    )

    prenotazioni = app_tables.prenotazioni.search(
        q.fetch_only(
            "telefono_wa",
            "nome_passeggero",
            passeggero=q.fetch_only("email"),
        ),
        tratta=tratta,
    )
    passeggeri = []
    for prenotazione in prenotazioni:
        passeggero = prenotazione["passeggero"]
        url = _url_whatsapp(prenotazione["telefono_wa"])
        if passeggero is None or url is None:
            continue
        nome = (
            prenotazione["nome_passeggero"]
            or passeggero["email"]
            or "passeggero"
        )
        passeggeri.append(
            {"text": "💬 Apri Chat WA — {}".format(nome), "url": url}
        )

    contatti = []
    dati_prenotazione = None
    if prenotazione_utente is not None:
        dati_prenotazione = {
            "id": prenotazione_utente.get_id(),
            "nome": prenotazione_utente["nome_passeggero"] or "",
            "telefono": prenotazione_utente["telefono_wa"] or "",
        }

    telefono_conducente = None
    if is_conducente:
        contatto_conducente = next(
            iter(app_tables.tratte_contatti.search(tratta=tratta)),
            None,
        )
        if contatto_conducente is not None:
            telefono_conducente = contatto_conducente["telefono_wa"]

    if is_conducente or prenotazione_utente is None:
        return {
            "prenotato": prenotazione_utente is not None,
            "passeggeri": passeggeri,
            "contatti": [],
            "prenotazione": dati_prenotazione,
            "telefono_conducente": telefono_conducente,
        }

    contatto_conducente = next(iter(app_tables.tratte_contatti.search(tratta=tratta)), None)
    url = (
        _url_whatsapp(contatto_conducente["telefono_wa"])
        if contatto_conducente is not None
        else None
    )
    if url is not None:
        contatti.append({"text": "💬 Apri Chat WA — Conducente", "url": url})

    return {
        "prenotato": True,
        "passeggeri": passeggeri,
        "contatti": contatti,
        "prenotazione": dati_prenotazione,
        "telefono_conducente": None,
    }


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
            from_address=_EMAIL_FROM_ADDRESS,
            subject="Attiva la tua auto per questa tratta",
            text=(
                "Le auto attive per la zona {} e il tipo di tratta {} "
                "hanno esaurito i posti disponibili. Se puoi, attiva la tua auto."
            ).format(zona, tipo_tratta),
        )
        email_inviate.add(email)

    return len(email_inviate)

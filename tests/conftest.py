"""Aucun réseau implicite pendant les tests locaux."""
import socket
import pytest

@pytest.fixture(autouse=True)
def pas_de_reseau_implicite(request, monkeypatch):
    if request.node.get_closest_marker('reseau'):
        return
    def interdit(*args, **kwargs):
        raise AssertionError('Réseau interdit dans un test local')
    monkeypatch.setattr(socket, 'create_connection', interdit)
    monkeypatch.setattr(socket.socket, 'connect', interdit)

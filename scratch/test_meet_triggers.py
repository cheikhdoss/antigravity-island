import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from island.meet_listener import is_teacher_question

test_cases = [
    ("c'est quoi une adresse ip ?", True),
    ("c est quoi un vpc", True),
    ("pourquoi dit-on que le cloud est scalable", True),
    ("qu'est-ce que vous comprenez par virtualisation", True),
    ("quelle est la différence entre tcp et udp", True),
    ("comment fonctionne un conteneur docker", True),
    ("qui peut me dire ce qu'est un sous-reseau", True),
    ("à quoi sert une passerelle internet", True),
    ("donnez-moi deux exemples de bases de données NoSQL", True),
    ("maintenant nous allons passer au chapitre suivant", False),
    ("voici la diapositive sur le protocole http", False),
    ("comme vous pouvez le voir le serveur est actif", False)
]

for text, expected in test_cases:
    res = is_teacher_question(text)
    print(f'["{text}"] -> {res} (Expected: {expected})')
    assert res == expected, f'Failed on: {text}'

print("=== ALL 12 TRIGGER CLASSIFICATION TESTS PASSED SUCCESSFULLY! ===")

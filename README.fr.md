# Plugin Hermes Capability Router

Ce dépôt contient un **plugin général Hermes**, et non un serveur MCP. Il
utilise les hooks publics de plugin pour fournir une recommandation de routage
avant la sélection d'un outil, sans modifier le cœur de Hermes.

**Langues :** [English](README.md) | [简体中文](README.zh-CN.md) | [Français](README.fr.md)

Licence : [MIT](LICENSE).

## Principe

Le plugin gère des **capacités** plutôt que des outils isolés.

```text
Capacité : extraction de texte d'image (OCR)
Implémentations : package Python PaddleOCR | CLI | API | outil MCP | modèle local
```

Une capacité reste stable ; son implémentation peut varier selon ce qui est
installé, le coût, la latence et les contraintes de la machine.

## Les deux cycles de vie

### 1. Routage à l'exécution : les trois couches

```text
Requête utilisateur
  -> Hook du plugin Hermes
  -> 1. Scene Router        (domaine : vision / document / coding)
  -> 2. Semantic Router     (intention : OCR / compréhension d'image)
  -> 3. Capability Resolver (recherche et classement des implémentations)
  -> recommandation injectée dans Hermes
  -> exécution Hermes ; garde de politique optionnelle
```

```text
Routage à l'exécution
├── Scene Router
├── Semantic Router
└── Capability Resolver
    ├── Capability Registry
    ├── Capability Index / recherche vectorielle locale
    └── classement des implémentations
        └── package Python | CLI | API | MCP | modèle local | plugin/skill
```

Exemple : `Extrais le texte de cette capture d'écran.`

```text
vision -> text_extraction -> vision.image_text_extraction
```

### 2. Découverte des capacités et annotation

Ce cycle s'exécute en arrière-plan. Une découverte crée un brouillon à réviser ;
elle n'active jamais automatiquement une capacité incertaine.

```text
Source installée ou externe
  -> Discovery Engine
  -> Annotation Engine
  -> révision humaine (pending review)
  -> Capability Registry
  -> Capability Index
```

```text
Discovery & Annotation
├── Discovery Engine
│   ├── plugins Hermes, packages Python et outils CLI
│   ├── dépôts GitHub et README
│   ├── outils MCP
│   └── modèles locaux
└── Annotation Engine
    ├── extraction des métadonnées
    ├── classification capacité / scène / intention
    ├── génération de tags multilingues
    ├── analyse des forces et limites
    └── file persistante de révision
```

Dans Hermes, utilisez `/capability-review` pour lister les brouillons, puis
`/capability-review approve <numéro>` après avoir vérifié la source et sa
disponibilité locale.

## Prise en charge linguistique

Les règles explicites couvrent le chinois simplifié, le chinois traditionnel,
le français et l'anglais. Les variantes françaises accentuées et non accentuées
sont incluses. Le modèle d'embedding multilingue local traite les paraphrases
qui ne correspondent pas aux règles.

```text
Français : Extrais le texte de cette capture d'écran.
中文      ：把这张截图里的文字提取出来
English  : Extract the text from this screenshot.
           -> vision -> text_extraction

Français : Qu'y a-t-il dans cette image ?
中文      ：这张图片里有什么？
English  : What is in this image?
           -> vision -> image_understanding
```

## Installer les embeddings locaux (facultatif)

Les embeddings ne sont pas obligatoires : les règles explicites continuent de
fonctionner sans modèle. Ils améliorent les paraphrases et les requêtes entre
langues.

Installez les dépendances dans le Python utilisé par Hermes :

```powershell
$HermesPython = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
& $HermesPython -m pip install "sentence-transformers>=2.7,<3" "huggingface-hub>=0.34,<1.0"
```

Téléchargez le modèle une fois avec Internet :

```powershell
& $HermesPython -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

La configuration active est ici :

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\data\router-config.json
```

```json
{
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "offline_only": true,
    "threshold": 0.42
  }
}
```

Redémarrez la Gateway après une modification. Gardez `offline_only` à `true`
après le téléchargement du modèle ; un `threshold` plus élevé rend le routage
plus strict.

## Remerciements et références amont

Ce plugin est une implémentation indépendante publiée sous licence MIT. Le
code source des projets ci-dessous n'est ni copié ni embarqué ici ; ils sont
cités pour une idée d'architecture ou une intégration facultative :

| Projet | Relation avec ce plugin |
| --- | --- |
| [aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router) | **Référence d'architecture uniquement.** Son approche route / utterance / seuil d'embedding a inspiré la frontière du Semantic Router ; le projet n'est ni importé, ni embarqué, ni requis à l'exécution. |
| [huggingface/sentence-transformers](https://github.com/huggingface/sentence-transformers) | **Dépendance d'exécution facultative.** Utilisée uniquement si le repli sémantique par embedding local est activé. |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | **Intégration facultative.** `ScraplingFetcher` ne sert à l'extraction HTML que lorsque la dépendance fetcher est installée. |
| [GitHub REST API](https://docs.github.com/en/rest) | **Interface de métadonnées externe.** Utilisée pour les descriptions de dépôt et la découverte de README ; les dépôts publics ne demandent pas de token. |

Veuillez consulter les licences et obligations d'attribution propres à chaque
projet amont.

## Installer le plugin

Copiez le contenu de `plugin/` dans :

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\
```

Redémarrez la Gateway Hermes, puis utilisez `hermes plugins list` pour vérifier
que le plugin est activé.

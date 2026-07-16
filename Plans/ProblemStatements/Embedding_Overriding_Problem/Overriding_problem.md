# Problem Statement

We need to identify an open-source agent or pipeline where the embedding logic can be safely overridden with a node- and component-aware re-embedding strategy. The change should improve embedding updates for modified parts of the codebase without breaking the rest of the system.

The override must stay compatible with the other pipeline components so the new embedding flow can be adopted without major changes elsewhere.
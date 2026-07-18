# Problem Statement

IN the current implementation of the code, a concept of commit stride has been introduced. If the commit stride is given as n, then every nth consecutive commit is retrieved from the given repo and the chosen commits at each nth step are used for calculating the subsequent drift. 

The current implementation of the parameterised function is hardcoded to be 20. It must be ensured that the parameter is dynamically passed to the function and it can take up multiple values. Accordingly, the total number of commits retrieved must be adjusted and the embeddings must be calculated for only the required commits at each nth step. 


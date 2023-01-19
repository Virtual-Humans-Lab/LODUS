Cenário A

Cenário B

Cenário C

Cenário D

Labels:

NoSkip0QuantityMovePopulation - em alguns casos o gather_population estava adicionando subactions de move_population com quantity = 0. Este arquivo deixa estas ações "passarem"

NoSkip0QuantityMovePopulation - Impede ações de move_population com quantity = 0 de passarem pelo gather_population

NotCounting0Quantity - esta versão não estava incluindo performance de ações de move_population que tinham quantity = 0, pois a função retornava antes da medida final.

Counting0Quantity - esta versão inclui a performance de ações de move_population com quantity = 0. Todos os cenário incluem esta performance, a menos que a label NotCounting0Quantity esteja explicita.

AdjustFilterAndGetPopulationOrder - o gather_population estava executando o get_population em todos os nodos antes dos filtros e 2 vezes (uma para salvar a popoulação disponivel e outra para verificar se ela é > 0). Isto foi ajustado para apenas uma execução. Também, casos onde um gather_population gerava move_population com quantity = 0 foram removidos
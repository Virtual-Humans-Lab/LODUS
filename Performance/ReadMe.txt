Cen�rio A

Cen�rio B

Cen�rio C

Cen�rio D

Labels:

NoSkip0QuantityMovePopulation - em alguns casos o gather_population estava adicionando subactions de move_population com quantity = 0. Este arquivo deixa estas a��es "passarem"

NoSkip0QuantityMovePopulation - Impede a��es de move_population com quantity = 0 de passarem pelo gather_population

NotCounting0Quantity - esta vers�o n�o estava incluindo performance de a��es de move_population que tinham quantity = 0, pois a fun��o retornava antes da medida final.

Counting0Quantity - esta vers�o inclui a performance de a��es de move_population com quantity = 0. Todos os cen�rio incluem esta performance, a menos que a label NotCounting0Quantity esteja explicita.

AdjustFilterAndGetPopulationOrder - o gather_population estava executando o get_population em todos os nodos antes dos filtros e 2 vezes (uma para salvar a popoula��o disponivel e outra para verificar se ela � > 0). Isto foi ajustado para apenas uma execu��o. Tamb�m, casos onde um gather_population gerava move_population com quantity = 0 foram removidos
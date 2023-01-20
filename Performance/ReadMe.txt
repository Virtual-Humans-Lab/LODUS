Cenário A - Rotina envolve apenas as GasStations. 100 ciclos (dias) são executados. Trabalhadores são pedidos a cada 4 horas, população geral e pedida e retornada a cada hora.

Cenário B - Cenário de exemplo. Contém apenas 3 regiões, cada uma com os nodos mais comuns. 1000 ciclos são executados. Populações são diretamente enviadas entre regiões. Alguns gather populations são usados 

Cenário C - Primeiros 4 cycle steps da cidade completa. Todos os pontos de interesse tem algum rotina. Porém, a população ainda não está muito dividida. Apenas 4 steps de 1 ciclo são executados

Cenário D - Ciclo inteiro da cidade completa. População começa a se dividir bastante após as 6 e 8 horas. 1 ciclo é executado.

Labels:

NoSkip0QuantityMovePopulation - em alguns casos o gather_population estava adicionando subactions de move_population com quantity = 0. Este arquivo deixa estas ações "passarem"

NoSkip0QuantityMovePopulation - Impede ações de move_population com quantity = 0 de passarem pelo gather_population

NotCounting0Quantity - esta versão não estava incluindo performance de ações de move_population que tinham quantity = 0, pois a função retornava antes da medida final.

Counting0Quantity - esta versão inclui a performance de ações de move_population com quantity = 0. Todos os cenário incluem esta performance, a menos que a label NotCounting0Quantity esteja explicita.

AdjustFilterAndGetPopulationOrder - o gather_population estava executando o get_population em todos os nodos antes dos filtros e 2 vezes (uma para salvar a popoulação disponivel e outra para verificar se ela é > 0). Isto foi ajustado para apenas uma execução. Também, casos onde um gather_population gerava move_population com quantity = 0 foram removidos

SegmentedSearch-XXpercent - ação de gather_population busca população em segmentos da lista de nodos. O tamanho do segmento é percentual ao tamanho da lista (com ceil para int) e definido por uma variável (XX da label). A lista de nodos é randomizada antes da busca para que nem sempre sejam os mesmos nodos a serem buscados

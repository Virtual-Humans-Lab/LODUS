Cen�rio A - Rotina envolve apenas as GasStations. 100 ciclos (dias) s�o executados. Trabalhadores s�o pedidos a cada 4 horas, popula��o geral e pedida e retornada a cada hora.

Cen�rio B - Cen�rio de exemplo. Cont�m apenas 3 regi�es, cada uma com os nodos mais comuns. 1000 ciclos s�o executados. Popula��es s�o diretamente enviadas entre regi�es. Alguns gather populations s�o usados 

Cen�rio C - Primeiros 4 cycle steps da cidade completa. Todos os pontos de interesse tem algum rotina. Por�m, a popula��o ainda n�o est� muito dividida. Apenas 4 steps de 1 ciclo s�o executados

Cen�rio D - Ciclo inteiro da cidade completa. Popula��o come�a a se dividir bastante ap�s as 6 e 8 horas. 1 ciclo � executado.

Labels:

NoSkip0QuantityMovePopulation - em alguns casos o gather_population estava adicionando subactions de move_population com quantity = 0. Este arquivo deixa estas a��es "passarem"

NoSkip0QuantityMovePopulation - Impede a��es de move_population com quantity = 0 de passarem pelo gather_population

NotCounting0Quantity - esta vers�o n�o estava incluindo performance de a��es de move_population que tinham quantity = 0, pois a fun��o retornava antes da medida final.

Counting0Quantity - esta vers�o inclui a performance de a��es de move_population com quantity = 0. Todos os cen�rio incluem esta performance, a menos que a label NotCounting0Quantity esteja explicita.

AdjustFilterAndGetPopulationOrder - o gather_population estava executando o get_population em todos os nodos antes dos filtros e 2 vezes (uma para salvar a popoula��o disponivel e outra para verificar se ela � > 0). Isto foi ajustado para apenas uma execu��o. Tamb�m, casos onde um gather_population gerava move_population com quantity = 0 foram removidos

SegmentedSearch-XXpercent - a��o de gather_population busca popula��o em segmentos da lista de nodos. O tamanho do segmento � percentual ao tamanho da lista (com ceil para int) e definido por uma vari�vel (XX da label). A lista de nodos � randomizada antes da busca para que nem sempre sejam os mesmos nodos a serem buscados

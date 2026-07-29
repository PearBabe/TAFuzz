initially { int x = 0; }

transition t [0,1] when (x == 0) { x = 1; }

check[zones,no_trace] mincost (x == 1)

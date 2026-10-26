# Resistência dos Materiais — Aula 1 (Ensino Técnico em Edificações)

> Material de exemplo (sintético) para teste do aplicativo. Substitua pelos
> slides reais do professor quando disponível.

## 1. Tensão normal
A tensão normal (σ) é a força axial (N) distribuída pela área da seção (A):
σ = N / A. Unidades: N/mm² (MPa). Em uma barra tracionada, quanto maior a
força ou menor a área, maior a tensão.

## 2. Deformação e Lei de Hooke
A deformação específica (ε) é a razão entre a variação de comprimento (ΔL) e o
comprimento inicial (L): ε = ΔL / L. No regime elástico vale a Lei de Hooke:
σ = E · ε, onde E é o módulo de elasticidade do material (ex.: aço E ≈ 200 GPa).

## 3. Vigas e momento fletor
Em uma viga biapoiada de vão L com carga uniformemente distribuída w (kN/m), o
momento fletor máximo ocorre no meio do vão: M_max = w · L² / 8. Já a reação em
cada apoio é R = w · L / 2.

Para uma carga pontual P no centro de uma viga biapoiada de vão L, o momento
máximo é M_max = P · L / 4.

## 4. Tensão de flexão
A tensão de flexão em uma seção é σ = M · c / I, onde M é o momento fletor, c é
a distância da linha neutra à fibra mais externa, e I é o momento de inércia da
seção. Para seção retangular de base b e altura h: I = b · h³ / 12.

## 5. Dimensionamento de pilares (carga axial)
A carga axial resistente de um pilar curto de concreto pode ser estimada por
N = σ_c · A, onde σ_c é a resistência à compressão do concreto e A a área da
seção. O índice de esbeltez λ = L_fl / i relaciona o comprimento de flambagem
L_fl com o raio de giração i da seção.

## 6. Conceitos qualitativos
- Materiais dúcteis (aço) deformam bastante antes de romper; frágeis (concreto
  simples) rompem com pouca deformação.
- O coeficiente de segurança compara a tensão resistente com a tensão atuante.
- Estados-limite: último (ruína) e de serviço (uso, deformações excessivas).

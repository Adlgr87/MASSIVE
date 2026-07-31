"""
Utilidades auxiliares para el simulador MASSIVE.

Este módulo contiene funciones helper para validación, clipping, 
generación de IDs y otras utilidades comunes.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import uuid


def clip_to_unit_interval(value: float) -> float:
    """Clippea un valor al intervalo [0, 1]."""
    return max(0.0, min(1.0, value))


def clip_array_to_unit_interval(arr: np.ndarray) -> np.ndarray:
    """Clippea un array numpy al intervalo [0, 1]."""
    return np.clip(arr, 0.0, 1.0)


def validate_opinion_range(opinions: np.ndarray, min_val: float, max_val: float) -> bool:
    """Valida que todas las opiniones estén dentro del rango especificado."""
    return np.all((opinions >= min_val) & (opinions <= max_val))


def generate_simulation_id() -> str:
    """Genera un ID único para una simulación."""
    return str(uuid.uuid4())[:8]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """División segura que evita división por cero."""
    if denominator == 0:
        return default
    return numerator / denominator


def normalize_array(arr: np.ndarray, epsilon: float = 1e-10) -> np.ndarray:
    """Normaliza un array para que sume 1."""
    total = np.sum(arr)
    if total < epsilon:
        return np.ones_like(arr) / len(arr)
    return arr / total


def calculate_variance(values: List[float]) -> float:
    """Calcula la varianza de una lista de valores."""
    if len(values) < 2:
        return 0.0
    mean = np.mean(values)
    return np.mean([(x - mean) ** 2 for x in values])


def calculate_std_dev(values: List[float]) -> float:
    """Calcula la desviación estándar de una lista de valores."""
    return np.sqrt(calculate_variance(values))


def is_converged(history: List[float], tolerance: float = 1e-6, window: int = 10) -> bool:
    """
    Verifica si una serie histórica ha convergido.
    
    Args:
        history: Lista de valores históricos
        tolerance: Tolerancia para considerar convergencia
        window: Ventana de tiempo para verificar
        
    Returns:
        True si la serie ha convergido
    """
    if len(history) < window:
        return False
    
    recent = history[-window:]
    return max(recent) - min(recent) < tolerance


def sigmoid(x: float, steepness: float = 1.0) -> float:
    """Función sigmoide."""
    return 1.0 / (1.0 + np.exp(-steepness * x))


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    """
    Función smoothstep para interpolación suave.
    
    Args:
        edge0: Borde inferior
        edge1: Borde superior
        x: Valor a interpolar
        
    Returns:
        Valor interpolado suavemente entre 0 y 1
    """
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def weighted_average(values: np.ndarray, weights: np.ndarray) -> float:
    """Calcula el promedio ponderado de valores."""
    if len(values) != len(weights):
        raise ValueError("values y weights deben tener la misma longitud")
    
    total_weight = np.sum(weights)
    if total_weight == 0:
        return np.mean(values)
    
    return np.sum(values * weights) / total_weight


def entropy(probabilities: np.ndarray) -> float:
    """
    Calcula la entropía de Shannon de una distribución de probabilidades.
    
    Args:
        probabilities: Array de probabilidades (debe sumar 1)
        
    Returns:
        Entropía de Shannon
    """
    # Filtrar ceros para evitar log(0)
    probs = probabilities[probabilities > 0]
    return -np.sum(probs * np.log2(probs))


def gini_coefficient(values: np.ndarray) -> float:
    """
    Calcula el coeficiente de Gini para medir desigualdad.
    
    Args:
        values: Array de valores
        
    Returns:
        Coeficiente de Gini (0 = igualdad perfecta, 1 = desigualdad perfecta)
    """
    if len(values) == 0:
        return 0.0
    
    sorted_values = np.sort(values)
    n = len(sorted_values)
    cumsum = np.cumsum(sorted_values)
    
    return (2 * np.sum((np.arange(1, n + 1) * sorted_values)) - (n + 1) * cumsum[-1]) / (n * cumsum[-1])


def running_mean(data: np.ndarray, window: int) -> np.ndarray:
    """
    Calcula el promedio móvil de una serie.
    
    Args:
        data: Serie de datos
        window: Tamaño de la ventana
        
    Returns:
        Serie con promedio móvil
    """
    if window <= 0 or window > len(data):
        return data.copy()
    
    result = np.zeros(len(data))
    for i in range(len(data)):
        start = max(0, i - window + 1)
        result[i] = np.mean(data[start:i+1])
    
    return result


def detect_peaks(data: np.ndarray, threshold: float = 0.5) -> List[int]:
    """
    Detecta picos en una serie de datos.
    
    Args:
        data: Serie de datos
        threshold: Umbral relativo para detectar picos
        
    Returns:
        Lista de índices donde hay picos
    """
    if len(data) < 3:
        return []
    
    peaks = []
    mean_val = np.mean(data)
    std_val = np.std(data)
    
    for i in range(1, len(data) - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            if data[i] > mean_val + threshold * std_val:
                peaks.append(i)
    
    return peaks


def exponential_moving_average(data: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """
    Calcula el promedio móvil exponencial.
    
    Args:
        data: Serie de datos
        alpha: Factor de suavizado (0 < alpha <= 1)
        
    Returns:
        Serie con EMA
    """
    if len(data) == 0:
        return data
    
    ema = np.zeros_like(data)
    ema[0] = data[0]
    
    for i in range(1, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
    
    return ema


def correlation_matrix(data: np.ndarray) -> np.ndarray:
    """
    Calcula la matriz de correlación entre variables.
    
    Args:
        data: Matrix donde cada columna es una variable
        
    Returns:
        Matriz de correlación
    """
    if data.ndim == 1:
        return np.array([[1.0]])
    
    return np.corrcoef(data, rowvar=False)


def pairwise_distances(points: np.ndarray) -> np.ndarray:
    """
    Calcula distancias euclidianas pairwise entre puntos.
    
    Args:
        points: Matrix de puntos (n_samples, n_features)
        
    Returns:
        Matriz de distancias (n_samples, n_samples)
    """
    n = len(points)
    distances = np.zeros((n, n))
    
    for i in range(n):
        for j in range(i+1, n):
            dist = np.sqrt(np.sum((points[i] - points[j])**2))
            distances[i, j] = dist
            distances[j, i] = dist
    
    return distances


def k_nearest_neighbors(distances: np.ndarray, k: int) -> List[List[int]]:
    """
    Encuentra los k vecinos más cercanos para cada punto.
    
    Args:
        distances: Matriz de distancias pairwise
        k: Número de vecinos
        
    Returns:
        Lista de listas con índices de vecinos
    """
    n = len(distances)
    neighbors = []
    
    for i in range(n):
        # Ordenar distancias excluyendo el propio punto
        sorted_indices = np.argsort(distances[i])
        # Tomar k vecinos (excluyendo el índice i mismo)
        k_neighbors = [idx for idx in sorted_indices if idx != i][:k]
        neighbors.append(k_neighbors)
    
    return neighbors


def adjacency_from_distances(distances: np.ndarray, threshold: float) -> np.ndarray:
    """
    Crea una matriz de adyacencia basada en umbral de distancia.
    
    Args:
        distances: Matriz de distancias pairwise
        threshold: Umbral de distancia para conectar nodos
        
    Returns:
        Matriz de adyacencia binaria
    """
    return (distances <= threshold).astype(int)


def degree_centrality(adjacency: np.ndarray) -> np.ndarray:
    """
    Calcula centralidad de grado para cada nodo.
    
    Args:
        adjacency: Matriz de adyacencia
        
    Returns:
        Array de centralidades de grado
    """
    degrees = np.sum(adjacency, axis=1)
    n = len(adjacency)
    
    if n <= 1:
        return np.zeros(n)
    
    return degrees / (n - 1)


def consensus_metric(opinions: np.ndarray) -> float:
    """
    Calcula una métrica de consenso basada en la varianza de opiniones.
    
    Args:
        opinions: Array de opiniones
        
    Returns:
        Métrica de consenso (1 = consenso perfecto, 0 = máximo desacuerdo)
    """
    if len(opinions) < 2:
        return 1.0
    
    variance = np.var(opinions)
    max_variance = 0.25  # Máxima varianza para opiniones en [-1, 1] o [0, 1]
    
    return 1.0 - min(1.0, variance / max_variance)


def polarization_index(opinions: np.ndarray) -> float:
    """
    Calcula un índice de polarización basado en bimodalidad.
    
    Args:
        opinions: Array de opiniones
        
    Returns:
        Índice de polarización (0 = sin polarización, 1 = máxima polarización)
    """
    if len(opinions) < 3:
        return 0.0
    
    # Histograma con 2 bins para detectar bimodalidad
    hist, _ = np.histogram(opinions, bins=2)
    
    # Polarización máxima cuando hay mitad en cada extremo
    expected = len(opinions) / 2
    deviation = abs(hist[0] - expected) / expected
    
    return 1.0 - deviation


def format_float(value: float, decimals: int = 4) -> str:
    """Formatea un float con número específico de decimales."""
    return f"{value:.{decimals}f}"


def format_scientific(value: float, precision: int = 3) -> str:
    """Formatea un float en notación científica."""
    return f"{value:.{precision}e}"


def batch_iterator(items: List[Any], batch_size: int):
    """
    Generador que itera sobre items en batches.
    
    Args:
        items: Lista de items a iterar
        batch_size: Tamaño de cada batch
        
    Yields:
        Batches de items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusiona dos diccionarios profundamente.
    
    Args:
        dict1: Primer diccionario
        dict2: Segundo diccionario (sobrescribe dict1)
        
    Returns:
        Diccionario fusionado
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def deep_copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Copia profunda de un diccionario."""
    import copy
    return copy.deepcopy(d)


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Aplana un diccionario anidado.
    
    Args:
        d: Diccionario a aplanar
        parent_key: Prefijo para claves
        sep: Separador entre niveles
        
    Returns:
        Diccionario aplanado
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def dict_to_namedtuple(d: Dict[str, Any], name: str = 'Result'):
    """Convierte un diccionario a namedtuple."""
    from collections import namedtuple
    return namedtuple(name, d.keys())(**d)


def safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Obtiene un valor de un diccionario de forma segura."""
    return d.get(key, default)


def set_nested_value(d: Dict[str, Any], keys: List[str], value: Any):
    """Establece un valor en un diccionario anidado."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def get_nested_value(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Obtiene un valor de un diccionario anidado."""
    try:
        for key in keys:
            d = d[key]
        return d
    except (KeyError, TypeError):
        return default


def validate_config(config: Dict[str, Any], schema: Dict[str, type]) -> Tuple[bool, List[str]]:
    """
    Valida un diccionario de configuración contra un schema.
    
    Args:
        config: Diccionario de configuración a validar
        schema: Schema con tipos esperados
        
    Returns:
        Tuple (es_valido, lista_de_errores)
    """
    errors = []
    
    for key, expected_type in schema.items():
        if key not in config:
            errors.append(f"Missing required key: {key}")
        elif not isinstance(config[key], expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type}, got {type(config[key])}")
    
    return len(errors) == 0, errors


def hash_dict(d: Dict[str, Any]) -> str:
    """Genera un hash consistente de un diccionario."""
    import hashlib
    import json
    
    # Serializar de forma determinista
    json_str = json.dumps(d, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()[:16]


def timestamp_to_str(timestamp: float, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Convierte timestamp a string formateado."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime(format)


def str_to_timestamp(date_str: str, format: str = '%Y-%m-%d %H:%M:%S') -> float:
    """Convierte string de fecha a timestamp."""
    from datetime import datetime
    return datetime.strptime(date_str, format).timestamp()


def progress_bar(current: int, total: int, prefix: str = '', length: int = 50) -> str:
    """
    Genera una barra de progreso en texto.
    
    Args:
        current: Progreso actual
        total: Total a completar
        prefix: Texto antes de la barra
        length: Longitud de la barra en caracteres
        
    Returns:
        String con barra de progreso
    """
    percent = current / total if total > 0 else 0
    filled_length = int(length * percent)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f'{prefix} |{bar}| {percent*100:.1f}% ({current}/{total})'


def retry_decorator(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorador para reintentar funciones fallidas.
    
    Args:
        max_attempts: Número máximo de intentos
        delay: Delay entre intentos en segundos
    """
    import time
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def memoize(func):
    """Decorador para memoización simple de funciones."""
    cache = {}
    
    @functools.wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    
    return wrapper


# Import functools para el decorador memoize
import functools

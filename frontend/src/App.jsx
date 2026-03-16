import { useEffect, useState } from 'react';
import PriceChart from './components/PriceChart';
import { fetchProducts } from './services/api';

function formatCurrency(value) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 2,
  }).format(value);
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [selectedUrl, setSelectedUrl] = useState('');
  const [selectedSeller, setSelectedSeller] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadProducts() {
      setLoading(true);
      setError('');
      try {
        const response = await fetchProducts();
        setProducts(response);
        if (response.length > 0) {
          setSelectedUrl((currentUrl) => currentUrl || response[0].urun_url);
        }
      } catch (requestError) {
        setError('Veri alinamadi. API sunucusunun calistigindan emin olun.');
      } finally {
        setLoading(false);
      }
    }
    loadProducts();
  }, []);

  const selectedProduct = products.find((product) => product.urun_url === selectedUrl) || products[0];
  const sellerNamesRaw = selectedProduct ? Object.keys(selectedProduct.saticilar || {}) : [];
  const sellerNames = sellerNamesRaw.filter((name) => name && name.toLowerCase() !== 'bilinmeyen');
  useEffect(() => {
    if (sellerNames.length > 0) {
      if (!selectedSeller || !sellerNames.includes(selectedSeller)) {
        setSelectedSeller(sellerNames[0]);
      }
      return;
    }
    if (sellerNamesRaw.length > 0 && !selectedSeller) {
      setSelectedSeller(sellerNamesRaw[0]);
    }
  }, [selectedProduct, sellerNames, sellerNamesRaw, selectedSeller]);

  const records = selectedProduct && selectedSeller && selectedProduct.saticilar[selectedSeller]
    ? selectedProduct.saticilar[selectedSeller]
    : [];
  const latestPrice = records.length ? records[records.length - 1].fiyat : null;
  const minPrice = records.length ? Math.min(...records.map((item) => item.fiyat)) : null;
  const maxPrice = records.length ? Math.max(...records.map((item) => item.fiyat)) : null;
  const lastUpdated = records.length
    ? new Date(records[records.length - 1].tarih).toLocaleString('tr-TR')
    : '-';

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Trendyol Fiyat Gözlem Paneli</p>
          <h1>Fiyat hareketlerini tek panelde takip edin.</h1>
          <p className="hero-copy">
            Selenium botu ile çekilen kayıtlar SQLite veritabanına düşer, FastAPI bu veriyi JSON olarak sunar ve panel grafik üzerinden değişimi gösterir.
          </p>
        </div>

        <div className="hero-actions">
          <label className="field-label" htmlFor="product-select">
            İzlenen ürün
          </label>
          <select
            id="product-select"
            value={selectedProduct?.urun_url ?? ''}
            onChange={(event) => {
              setSelectedUrl(event.target.value);
              setSelectedSeller('');
            }}
            disabled={!products.length}
          >
            {products.length === 0 && <option value="">Kayıtlı ürün yok</option>}
            {products.map((product) => (
              <option key={product.urun_url} value={product.urun_url}>
                {product.urun_adi}
              </option>
            ))}
          </select>

          <label className="field-label" htmlFor="seller-select" style={{ marginLeft: 16 }}>
            Satıcı
          </label>
          <select
            id="seller-select"
            value={selectedSeller}
            onChange={(event) => setSelectedSeller(event.target.value)}
            disabled={!sellerNames.length}
          >
            {sellerNames.length === 0 && <option value="">Satıcı yok</option>}
            {sellerNames.map((seller) => (
              <option key={seller} value={seller}>{seller}</option>
            ))}
          </select>

          <button type="button" className="refresh-button" onClick={() => window.location.reload()}>
            Veriyi yenile
          </button>
        </div>
      </section>

      {error && <section className="status-card error-card">{error}</section>}
      {loading && <section className="status-card">Veriler yükleniyor...</section>}

      {!loading && !error && (
        <>
          <section className="stats-grid">
            <article className="stat-card">
              <span>Son fiyat</span>
              <strong>{latestPrice !== null ? formatCurrency(latestPrice) : '-'}</strong>
            </article>
            <article className="stat-card">
              <span>En düşük</span>
              <strong>{minPrice !== null ? formatCurrency(minPrice) : '-'}</strong>
            </article>
            <article className="stat-card">
              <span>En yüksek</span>
              <strong>{maxPrice !== null ? formatCurrency(maxPrice) : '-'}</strong>
            </article>
            <article className="stat-card">
              <span>Kayıt adedi</span>
              <strong>{records.length}</strong>
            </article>
            <article className="stat-card">
              <span>Son güncelleme</span>
              <strong className="stat-small">{lastUpdated}</strong>
            </article>
            <article className="stat-card">
              <span>Satıcı</span>
              <strong>{selectedSeller}</strong>
            </article>
          </section>

          <section className="content-grid">
            <article className="panel-card chart-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Fiyat Geçmişi</p>
                  <h2>{selectedProduct?.urun_adi ?? 'Veri bekleniyor'} <span style={{fontWeight:400, fontSize:'1rem'}}>({selectedSeller})</span></h2>
                </div>
              </div>
              <PriceChart data={records} />
            </article>

            <article className="panel-card history-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Ham Kayıtlar</p>
                  <h2>Son ölçümler</h2>
                </div>
              </div>

              <div className="history-list">
                {records.length === 0 && <p>Seçili ürün ve satıcı için henüz veri yok.</p>}
                {records
                  .slice()
                  .reverse()
                  .map((item) => (
                    <div key={item.id} className="history-item">
                      <strong>{formatCurrency(item.fiyat)}</strong>
                      <span>{new Date(item.tarih).toLocaleString('tr-TR')}</span>
                    </div>
                  ))}
              </div>
            </article>
          </section>
        </>
      )}
    </main>
  );
}

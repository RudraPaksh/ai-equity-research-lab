import 'zone.js';

import { bootstrapApplication } from '@angular/platform-browser';
import {
  HttpClient,
  provideHttpClient,
  HttpErrorResponse
} from '@angular/common/http';
import {
  Component,
  computed,
  inject,
  signal
} from '@angular/core';
import { CommonModule, DecimalPipe, PercentPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

type AnyMap = Record<string, any>;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DecimalPipe,
    PercentPipe
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  symbolResults: AnyMap[] = [];
showSymbolResults = false;
symbolSearchLoading = false;

  private readonly http: HttpClient = inject(HttpClient);

  readonly api = 'http://127.0.0.1:8000/api';

  symbol = 'AAPL';
  activeTab = 'Overview';

  loading = signal<boolean>(false);
  error = signal<string>('');

  stock = signal<AnyMap | null>(null);
  fundamentals = signal<AnyMap | null>(null);
  news = signal<AnyMap | null>(null);
  dcf = signal<AnyMap | null>(null);
  forecast = signal<AnyMap | null>(null);
forecastLoading = signal<boolean>(false);

  dcfLoading = signal<boolean>(false);
  analyst = signal<AnyMap | null>(null);
analystLoading = signal<boolean>(false);
analystError = signal<string>('');

  dcfInput: AnyMap = {
    revenue: 400000,
    shares: 15000,
    growth: 0.08,
    fcf_margin: 0.24,
    wacc: 0.09,
    terminal_growth: 0.03,
    net_debt: 50000,
    years: 5
  };

  tabs: string[] = [
    'Overview',
    'Valuation',
    'Financials',
    'News',
    'AI Research'
  ];

  factorRows = computed(() => {
    const factors = this.stock()?.factors ?? {};

    return Object.entries(factors).map(
      ([key, value]: [string, any]) => ({
        key: key.replaceAll('_', ' '),
        value: Number(value) || 0,
        positive: Number(value) >= 60
      })
    );
  });

  selectedSecurity = signal<AnyMap | null>(null);

get securityExchange(): string {
  return String(
    this.selectedSecurity()?.exchange ?? '—'
  );
}

get securityCountry(): string {
  return String(
    this.selectedSecurity()?.country ?? '—'
  );
}

get securityCurrency(): string {
  return String(
    this.selectedSecurity()?.currency ?? '—'
  );
}

get securityName(): string {
  return String(
    this.selectedSecurity()?.name ?? this.symbol
  );
}

  get price(): number {
    return Number(
      this.stock()?.risk?.latest_price ?? 0
    );
  }

  get upProbability(): number {
    return Number(
      this.stock()?.prediction?.p_up ?? 0
    );
  }

  get downProbability(): number {
    return Number(
      this.stock()?.prediction?.p_down ?? 0
    );
  }

  get signal(): string {
    return String(
      this.stock()?.prediction?.signal ??
      'Awaiting analysis'
    );
  }

  get modelName(): string {
    return String(
      this.stock()?.backtest?.selected_model ?? '—'
    );
  }

  get accuracy(): number {
    return Number(
      this.stock()?.backtest?.accuracy ?? 0
    );
  }

  get volatility(): number {
    return Number(
      this.stock()?.risk?.annualized_volatility ?? 0
    );
  }

  get drawdown(): number {
    return Number(
      this.stock()?.risk?.max_drawdown ?? 0
    );
  }

  get sharpe(): number {
    return Number(
      this.stock()?.risk?.sharpe_approx ?? 0
    );
  }

  get rocAuc(): number {
    return Number(
      this.stock()?.backtest?.roc_auc ?? 0
    );
  }

  analyze(symbol: string = this.symbol): void {

    const clean: string = symbol.trim().toUpperCase();

    if (!clean) {
      return;
    }

    this.symbol = clean;
    this.loading.set(true);
    this.error.set('');
    this.activeTab = 'Overview';

    this.http
      .get<AnyMap>(
        `${this.api}/stock/${encodeURIComponent(clean)}`
      )
      .subscribe({
        next: (data: AnyMap): void => {
          this.stock.set(data);
          this.loading.set(false);

          this.loadSecondaryData(clean);
           // AI forecast
  this.loadForecast(clean);
   this.loadAnalyst(clean);
        },

        error: (err: HttpErrorResponse): void => {
          this.loading.set(false);

          this.error.set(
            this.getErrorMessage(
              err,
              'Unable to load market data. Check your API key and backend.'
            )
          );
        }
      });
  }

  loadSecondaryData(symbol: string): void {

    this.http
      .get<AnyMap>(
        `${this.api}/fundamentals/${encodeURIComponent(symbol)}`
      )
      .subscribe({
        next: (data: AnyMap): void => {
          this.fundamentals.set(data);
        },

        error: (_err: HttpErrorResponse): void => {
          this.fundamentals.set(null);
        }
      });

    this.http
      .get<AnyMap>(
        `${this.api}/news/${encodeURIComponent(symbol)}`
      )
      .subscribe({
        next: (data: AnyMap): void => {
          this.news.set(data);
        },

        error: (_err: HttpErrorResponse): void => {
          this.news.set(null);
        }
      });
  }

  loadForecast(symbol: string): void {

  this.forecastLoading.set(true);

  this.http
    .get<AnyMap>(
      `${this.api}/forecast/${encodeURIComponent(symbol)}`
    )
    .subscribe({

      next: (data: AnyMap): void => {
        console.log('Forecast received:', data);
        this.forecast.set(data);
        this.forecastLoading.set(false);
      },

      error: (err: HttpErrorResponse): void => {
        console.error('Forecast API error:', err);

        this.forecast.set(null);
        this.forecastLoading.set(false);
      }

    });
}
loadAnalyst(symbol: string): void {
  this.analystLoading.set(true);
  this.analystError.set('');

  this.http
    .get<AnyMap>(
      `${this.api}/analyst/${encodeURIComponent(symbol)}`
    )
    .subscribe({
      next: (data: AnyMap): void => {
        console.log('AI Analyst received:', data);

        this.analyst.set(data);
        this.analystLoading.set(false);
      },

      error: (err: HttpErrorResponse): void => {
        console.error('AI Analyst API error:', err);

        this.analyst.set(null);
        this.analystLoading.set(false);

        this.analystError.set(
          this.getErrorMessage(
            err,
            'AI Analyst could not generate the research report.'
          )
        );
      }
    });
}
  calculateDcf(): void {

    this.dcfLoading.set(true);
    this.error.set('');

    this.http
      .post<AnyMap>(
        `${this.api}/dcf`,
        this.dcfInput
      )
      .subscribe({
        next: (data: AnyMap): void => {
          this.dcf.set(data);
          this.dcfLoading.set(false);
        },

        error: (err: HttpErrorResponse): void => {
          this.dcfLoading.set(false);

          this.error.set(
            this.getErrorMessage(
              err,
              'DCF calculation failed.'
            )
          );
        }
      });
  }

  setTab(tab: string): void {

    this.activeTab = tab;

    if (
      tab === 'Valuation' &&
      !this.dcf()
    ) {
      this.calculateDcf();
    }
  }

 quickSearch(ticker: string): void {

  this.symbol = ticker.toUpperCase();

  this.http
    .get<AnyMap>(
      `${this.api}/symbol/search`,
      {
        params: {
          q: ticker,
          limit: '1'
        }
      }
    )
    .subscribe({
      next: (data: AnyMap): void => {

        const first = data.results?.[0];

        if (first) {
          this.selectedSecurity.set(first);
        }

        this.analyze(ticker);
      },

      error: (): void => {
        this.analyze(ticker);
      }
    });
}

  metricLabel(value: number): string {

    if (value >= 75) {
      return 'Strong';
    }

    if (value >= 55) {
      return 'Positive';
    }

    if (value >= 40) {
      return 'Neutral';
    }

    return 'Weak';
  }

  barWidth(value: number): number {
    return Math.max(
      4,
      Math.min(100, value)
    );
  }
onSymbolInput(): void {

  const query = this.symbol.trim();

  this.showSymbolResults = false;
  this.symbolResults = [];

  if (query.length < 2) {
    return;
  }

  this.symbolSearchLoading = true;

  this.http
    .get<AnyMap>(
      `${this.api}/symbol/search`,
      {
        params: {
          q: query,
          limit: '8'
        }
      }
    )
    .subscribe({

      next: (data: AnyMap): void => {

        this.symbolResults = data.results ?? [];

        this.showSymbolResults =
          this.symbolResults.length > 0;

        this.symbolSearchLoading = false;
      },

      error: (_err: HttpErrorResponse): void => {

        this.symbolResults = [];
        this.showSymbolResults = false;
        this.symbolSearchLoading = false;
      }

    });
}

selectSymbol(result: AnyMap): void {

  this.selectedSecurity.set(result);

  this.symbol = String(
    result.symbol ?? ''
  ).toUpperCase();

  this.showSymbolResults = false;
  this.symbolResults = [];

  this.analyze(this.symbol);
}


  private getErrorMessage(
    err: HttpErrorResponse,
    fallback: string
  ): string {

    if (typeof err.error === 'string') {
      return err.error;
    }

    if (
      err.error &&
      typeof err.error === 'object' &&
      'detail' in err.error
    ) {
      return String(
        (err.error as AnyMap)['detail']
      );
    }

    if (err.message) {
      return err.message;
    }

    return fallback;
  }
}

bootstrapApplication(App, {
  providers: [
    provideHttpClient()
  ]
})
  .then(() => {
    console.log('AI Equity Research Lab started');
  })
  .catch((err: unknown) => {
    console.error(
      'Angular bootstrap failed:',
      err
    );
  });

  
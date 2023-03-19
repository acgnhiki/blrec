import { NgxLoggerLevel } from 'ngx-logger';

export const environment = {
  production: true,
  apiBaseUrl: '',
  webSocketBaseUrl: '',
  ngxLoggerLevel: NgxLoggerLevel.DEBUG,
  traceRouterScrolling: false,
} as const;

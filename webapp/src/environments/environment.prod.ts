import { NgxLoggerLevel } from 'ngx-logger';

export const environment = {
  production: true,
  apiUrl: '',
  webSocketUrl: '',
  ngxLoggerLevel: NgxLoggerLevel.DEBUG,
  traceRouterScrolling: false,
} as const;

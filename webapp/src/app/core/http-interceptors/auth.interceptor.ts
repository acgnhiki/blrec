import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { catchError, retry } from 'rxjs/operators';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private auth: AuthService) {}

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    return next
      .handle(
        request.clone({ setHeaders: { 'X-API-KEY': this.auth.getApiKey() } })
      )
      .pipe(
        catchError((error: HttpErrorResponse) => {
          if (error.status === 401) {
            // Unauthorized
            if (this.auth.hasApiKey()) {
              this.auth.removeApiKey();
            }
            const apiKey = window.prompt('API Key:') ?? '';
            this.auth.setApiKey(apiKey);
          }
          throw error;
        }),
        retry(3)
      );
  }
}

import { TestBed } from '@angular/core/testing';

import { WebhookSettingsResolver } from './webhook-settings.resolver';

describe('WebhookSettingsResolverService', () => {
  let service: WebhookSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(WebhookSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});

import { TestBed } from '@angular/core/testing';

import { AppInfoResolver } from './app-info.resolver';

describe('AppInfoResolver', () => {
  let resolver: AppInfoResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    resolver = TestBed.inject(AppInfoResolver);
  });

  it('should be created', () => {
    expect(resolver).toBeTruthy();
  });
});

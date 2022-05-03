import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PushdeerSettingsComponent } from './pushdeer-settings.component';

describe('PushdeerSettingsComponent', () => {
  let component: PushdeerSettingsComponent;
  let fixture: ComponentFixture<PushdeerSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PushdeerSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PushdeerSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

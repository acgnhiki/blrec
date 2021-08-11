import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NotifierSettingsComponent } from './notifier-settings.component';

describe('NotifierSettingsComponent', () => {
  let component: NotifierSettingsComponent;
  let fixture: ComponentFixture<NotifierSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NotifierSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NotifierSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BiliApiSettingsComponent } from './bili-api-settings.component';

describe('BiliApiSettingsComponent', () => {
  let component: BiliApiSettingsComponent;
  let fixture: ComponentFixture<BiliApiSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ BiliApiSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BiliApiSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

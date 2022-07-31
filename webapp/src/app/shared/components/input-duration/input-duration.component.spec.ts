import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InputDurationComponent } from './input-duration.component';

describe('InputDurationComponent', () => {
  let component: InputDurationComponent;
  let fixture: ComponentFixture<InputDurationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ InputDurationComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(InputDurationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

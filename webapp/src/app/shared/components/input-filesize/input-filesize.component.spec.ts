import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InputFilesizeComponent } from './input-filesize.component';

describe('InputFilesizeComponent', () => {
  let component: InputFilesizeComponent;
  let fixture: ComponentFixture<InputFilesizeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ InputFilesizeComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(InputFilesizeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

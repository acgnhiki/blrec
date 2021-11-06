import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskPostprocessingDetailComponent } from './task-postprocessing-detail.component';

describe('TaskPostprocessingDetailComponent', () => {
  let component: TaskPostprocessingDetailComponent;
  let fixture: ComponentFixture<TaskPostprocessingDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskPostprocessingDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskPostprocessingDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
